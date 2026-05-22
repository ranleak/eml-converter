import os
import sys
import email
from email import policy
import pdfkit

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Initialize Rich Console
console = Console()

def parse_eml(file_path):
    """Parses the EML file and extracts headers and body content."""
    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    # Extract headers
    headers = {
        "Subject": msg.get("Subject", "No Subject"),
        "From": msg.get("From", "Unknown Sender"),
        "To": msg.get("To", "Unknown Recipient"),
        "Date": msg.get("Date", "Unknown Date")
    }
    
    # Extract the most appropriate body (prefers HTML, falls back to plain text)
    body = msg.get_body(preferencelist=('html', 'plain'))
    
    if body:
        content = body.get_content()
        is_html = (body.get_content_type() == 'text/html')
    else:
        content = "No readable content found in this email."
        is_html = False
        
    return headers, content, is_html

def generate_html_string(headers, content, is_html):
    """Wraps the email data into a neat HTML template."""
    
    # If the content is plain text, wrap it in <pre> tags to preserve formatting
    if not is_html:
        content = f"<pre style='white-space: pre-wrap; font-family: inherit;'>{content}</pre>"

    html_template = f"""
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
    return html_template

def main():
    console.print(Panel.fit("[bold blue]EML to HTML & PDF Converter[/bold blue]\n[dim]Powered by Python, Rich, and PDFKit[/dim]", border_style="blue"))
    
    # 1. Prompt for input file
    while True:
        eml_path = Prompt.ask("[bold yellow]Enter the path to your .eml file[/bold yellow]")
        if os.path.isfile(eml_path) and eml_path.lower().endswith('.eml'):
            break
        console.print("[bold red]✖ Error:[/bold red] File not found or not a valid .eml file. Please try again.")

    # 2. Determine output filenames based on input
    base_name = os.path.splitext(eml_path)[0]
    html_out = f"{base_name}.html"
    pdf_out = f"{base_name}.pdf"

    try:
        # 3. Process the file with a Rich status spinner
        with console.status("[bold cyan]Reading and parsing EML file...", spinner="dots"):
            headers, content, is_html = parse_eml(eml_path)
            html_string = generate_html_string(headers, content, is_html)
        console.print("[bold green]✔[/bold green] EML parsed successfully!")

        # 4. Save HTML
        with console.status("[bold cyan]Saving HTML file...", spinner="dots"):
            with open(html_out, "w", encoding="utf-8") as f:
                f.write(html_string)
        console.print(f"[bold green]✔[/bold green] HTML saved to: [bold white]{html_out}[/bold white]")

        # 5. Convert to PDF
        with console.status("[bold cyan]Converting HTML to PDF (this may take a moment)...", spinner="dots"):
            # Disable pdfkit console output for a cleaner UI
            options = {'quiet': ''} 
            pdfkit.from_string(html_string, pdf_out, options=options)
        console.print(f"[bold green]✔[/bold green] PDF saved to: [bold white]{pdf_out}[/bold white]")

        # Success message
        success_msg = Text.assemble(
            ("Conversion Complete!\n", "bold green"),
            ("HTML: ", "bold"), (f"{html_out}\n", "cyan"),
            ("PDF: ", "bold"), (f"{pdf_out}", "cyan")
        )
        console.print(Panel(success_msg, border_style="green", expand=False))

    except OSError as e:
        if "wkhtmltopdf" in str(e).lower():
            console.print("\n[bold red]✖ Missing System Dependency![/bold red]")
            console.print("It looks like [bold]wkhtmltopdf[/bold] is not installed or not in your system PATH.")
            console.print("Please install it from [link=https://wkhtmltopdf.org/downloads.html]https://wkhtmltopdf.org/downloads.html[/link] and try again.")
        else:
            console.print(f"\n[bold red]✖ OS Error:[/bold red] {e}")
    except Exception as e:
         console.print(f"\n[bold red]✖ An unexpected error occurred:[/bold red] {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
        sys.exit(0)