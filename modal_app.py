import email
from email import policy
import fastapi
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import Response, RedirectResponse
import modal

# 1. Define the Modal App container
app = modal.App("eml-converter-service")

# 2. Configure the remote Linux environment with system & Python dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("wkhtmltopdf")
    .pip_install("fastapi[standard]", "pdfkit")
)

# 3. Initialize your core FastAPI application
web_app = FastAPI(
    title="EML to HTML/PDF Converter API",
    description="Serverless API to convert uploaded .eml files into clean HTML or PDFs.",
    version="1.0.0"
)

def parse_eml_bytes(content_bytes: bytes):
    """Parses raw EML binary data to extract headers and readable body content."""
    msg = email.message_from_bytes(content_bytes, policy=policy.default)
    
    headers = {
        "Subject": msg.get("Subject", "No Subject"),
        "From": msg.get("From", "Unknown Sender"),
        "To": msg.get("To", "Unknown Recipient"),
        "Date": msg.get("Date", "Unknown Date")
    }
    
    # Prioritize HTML version of the email body, fallback to plain text
    body = msg.get_body(preferencelist=('html', 'plain'))
    if body:
        content = body.get_content()
        is_html = (body.get_content_type() == 'text/html')
    else:
        content = "No readable content found in this email."
        is_html = False
        
    return headers, content, is_html

def generate_html_string(headers: dict, content: str, is_html: bool) -> str:
    """Wraps email context within a standard HTML rendering canvas."""
    if not is_html:
        content = f"<pre style='white-space: pre-wrap; font-family: inherit;'>{content}</pre>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
            .header {{ 
                border-bottom: 2px solid #0056b3; 
                padding-bottom: 15px; 
                margin-bottom: 20px; 
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
            }}
            .header p {{ margin: 5px 0; }}
            .content {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        <div class="header">
            <p><strong>Subject:</strong> {headers['Subject']}</p>
            <p><strong>From:</strong> {headers['From']}</p>
            <p><strong>To:</strong> {headers['To']}</p>
            <p><strong>Date:</strong> {headers['Date']}</p>
        </div>
        <div class="content">
            {content}
        </div>
    </body>
    </html>
    """

@web_app.get("/")
async def root():
    """Redirects the base URL to the interactive API documentation."""
    return RedirectResponse(url="/docs")

@web_app.post("/convert")
async def convert_eml(
    file: UploadFile = File(...),
    output_format: str = Query("pdf", description="Choose output format: 'pdf' or 'html'")
):
    """Accepts an .eml upload and returns either a rendered .html or .pdf download."""
    if not file.filename.lower().endswith('.eml'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .eml files are accepted.")
    
    try:
        content_bytes = await file.read()
        headers, content, is_html = parse_eml_bytes(content_bytes)
        html_string = generate_html_string(headers, content, is_html)
        
        # Base file name for output naming
        base_filename = file.filename.rsplit('.', 1)[0]
        
        if output_format.lower() == "html":
            return Response(
                content=html_string,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={base_filename}.html"}
            )
            
        elif output_format.lower() == "pdf":
            import pdfkit
            options = {'quiet': '', 'enable-local-file-access': ''}
            
            # Setting the second parameter to False returns the compiled PDF file raw data directly as bytes
            pdf_bytes = pdfkit.from_string(html_string, False, options=options)
            
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={base_filename}.pdf"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported output format. Choose 'pdf' or 'html'.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

# 4. Expose the FastAPI app routing context back to Modal's ASGI web pipeline
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app