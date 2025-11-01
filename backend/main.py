from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import shutil
import easyocr
import cv2
import numpy as np

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# Khởi tạo EasyOCR
reader = easyocr.Reader(['vi', 'en'])

@app.get('/')
async def read_root():
    # Trả về HTML đơn giản
    html_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart OCR System</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
            .result-area { margin-top: 30px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Smart OCR System</h1>
            <p>Tải lên hình ảnh để nhận dạng văn bản</p>
            
            <div class="upload-area">
                <form id="uploadForm" enctype="multipart/form-data">
                    <input type="file" id="fileInput" accept="image/*" />
                    <br><br>
                    <button type="submit">Nhận dạng văn bản</button>
                </form>
            </div>
            
            <div class="result-area" id="resultArea" style="display:none;">
                <h3>Kết quả nhận dạng:</h3>
                <div id="resultText"></div>
            </div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                const fileInput = document.getElementById('fileInput');
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    const response = await fetch('/ocr', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('resultText').innerHTML = 
                            '<p><strong>File:</strong> ' + result.filename + '</p>' +
                            '<p><strong>Độ tin cậy:</strong> ' + result.confidence + '%</p>' +
                            '<p><strong>Số dòng:</strong> ' + result.line_count + '</p>' +
                            '<pre style="background: #f5f5f5; padding: 15px; border-radius: 5px;">' + result.text + '</pre>';
                        document.getElementById('resultArea').style.display = 'block';
                    } else {
                        alert('Lỗi: ' + result.error);
                    }
                } catch (error) {
                    alert('Lỗi kết nối: ' + error);
                }
            });
        </script>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content)

@app.post('/ocr')
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        # Lưu file upload
        filename = file.filename
        file_path = f'uploads/{filename}'
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Xử lý OCR với EasyOCR
        result = reader.readtext(file_path)
        
        # Trích xuất text từ kết quả
        text_lines = []
        confidences = []
        
        for detection in result:
            text = detection[1]
            confidence = detection[2]
            text_lines.append(text)
            confidences.append(confidence)
        
        full_text = '\n'.join(text_lines)
        avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0
        
        return {
            'success': True,
            'filename': filename,
            'text': full_text,
            'confidence': round(avg_confidence, 2),
            'line_count': len(text_lines),
            'lines': [{'text': text, 'confidence': conf} for text, conf in zip(text_lines, confidences)]
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
