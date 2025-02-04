import os
import re
import datetime
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.abspath('logs')
JAVASCRIPT = '/static/script.js?v=1.0.3'

# Symbols in HTML code
RED = '#ff0000'
GREEN = '#0BDA51'
CIRCLE = '&#11044;'
TRIANGLE_DOWN = '&#9660;'
TRIANGLE_RIGHT = '&#9654;'

# ANSI escape code to HTML style mapping
ANSI_COLORS = {
    "30": "color: black;",
    "31": "color: red;",
    "32": "color: green;",
    "33": "color: yellow;",
    "34": "color: blue;",
    "35": "color: magenta;",
    "36": "color: cyan;",
    "37": "color: white;",
    "90": "color: gray;",
    "91": "color: lightcoral;",
    "92": "color: lightgreen;",
    "93": "color: lightyellow;",
    "94": "color: lightblue;",
    "95": "color: lightpink;",
    "96": "color: lightcyan;",
    "97": "color: white;",
    "1": "font-weight: bold;",
    "4": "text-decoration: underline;",
}

# ANSI_ESCAPE_RE = re.compile(r'\\u001b\[(\d+)(?:;(\d+))?(?:;(\d+))?m')
ANSI_ESCAPE_RE = re.compile(r'\\u001b\[([1-9]+)(?:;(\d+))?(?:;(\d+))?m')

# Used as a unique identifier for JavaScript
initial_time = str(datetime.datetime.now())


def ansi_to_html(text):
    """Converts ANSI escape codes to HTML span elements."""
    def replace_ansi(match):
        codes = match.groups()
        styles = [ANSI_COLORS.get(code, "") for code in codes if code]
        return f'<span style="{" ".join(styles)}">'

    # Replace ANSI codes with styled <span> elements
    text = ANSI_ESCAPE_RE.sub(replace_ansi, text)

    # Close spans when the reset code \u001b[0m is found
    text = text.replace("\\u001b[0m", "</span>")
    return text


class CustomHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Disable caching
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()
    
    def do_GET(self):
           
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Serve sidebar dynamically
        if parsed_path.path.startswith("/get_sidebar"):
            sidebar_html = self.generate_sidebar(BASE_DIR)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(sidebar_html.encode())
            return

        # Serve dynamic file content
        if parsed_path.path.startswith("/get_file_content"):
            query_params = urllib.parse.parse_qs(parsed_path.query)
            file_path = query_params.get("path", [""])[0]
            full_path = os.path.join(BASE_DIR, file_path)

            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    content = ansi_to_html(content)
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return
                except Exception:
                    self.send_error(500, "Error reading file")
                    return
            
            self.send_error(404, "File not found")
            return

        # Serve text files
        file_path = os.path.join(BASE_DIR, parsed_path.path.lstrip("/"))
        if file_path.endswith(".txt") or parsed_path.path.startswith("/view/"):
            self.serve_main_page()
        elif os.path.isdir(file_path):
            self.serve_main_page()
        else:
            return super().do_GET()
        
        
    def serve_main_page(self):
        """Serve the main HTML page once, and update content dynamically."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        sidebar_html = self.generate_sidebar(BASE_DIR)

        self.wfile.write(f"""
        <html>
        <head>
            <title>File Viewer</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
            <script src={JAVASCRIPT} defer></script>
        </head>
        <body>
            <div class="sidebar">
                {sidebar_html}
            </div>
            <div class="content">
                <h2 id="file-title">Select a file</h2>
                <pre id="file-content">Click on a file to view its content.</pre>
            </div>
        </body>
        </html>
        """.encode())



    def list_directory(self, dir_path):
        try:
            entries = os.listdir(dir_path)
            entries.sort()
            relative_path = os.path.relpath(dir_path, BASE_DIR)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            self.wfile.write(f"""
            <html>
            <head>
                <title>Directory: {relative_path}</title>
                <link rel="stylesheet" type="text/css" href="/static/style.css">
                <script src={JAVASCRIPT} defer></script>
            </head>
            <body>
                <div class="sidebar">
                    {self.generate_sidebar(BASE_DIR)}
                </div>
                <div class="content">
                    <h2>{relative_path}</h2>
                    <ul>
            """.encode())

            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                url_path = urllib.parse.quote(os.path.join(relative_path, entry).replace("\\", "/"))
                display_name = entry + ("/" if os.path.isdir(full_path) else "")
                self.wfile.write(f'<li><a href="/{url_path}">{display_name}</a></li>'.encode())

            self.wfile.write(b"</ul></div></body></html>")

        except OSError:
            self.send_error(404, "Directory not found")
            

    def serve_text_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            content = ansi_to_html(content)  # Convert ANSI to HTML

            relative_path = os.path.relpath(file_path, BASE_DIR)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
            <html>
            <head>
                <title>{relative_path}</title>
                <link rel="stylesheet" type="text/css" href="/static/style.css">
                <script src={JAVASCRIPT} defer></script>
            </head>
            <body data-file-path="{relative_path}">
                <div class="sidebar">
                    {self.generate_sidebar(BASE_DIR)}
                </div>
                <div class="content">
                    <h2>{relative_path}</h2>
                    <pre id="file-content">{content}</pre>
                </div>
            </body>
            </html>
            """.encode())

        except OSError:
            self.send_error(404, "File not found")
            

    def generate_sidebar(self, base_path):
        def build_tree(path, rel_path=""):
            items = sorted(os.listdir(path))  # Sort items alphabetically
            html = "<ul>"
            directory_contains_error = False  # Track if any file inside has "Error"
            
            for item in items:
                full_path = os.path.join(path, item)
                unique_id = full_path + initial_time # Unique identifier for JS
                relative_path = os.path.relpath(full_path, base_path)
                url_path = urllib.parse.quote(relative_path.replace("\\", "/"))
                
                display_name = item  # Default display name
                item_contains_error = False  # Track errors for this item

                # If it's a file, check for "Error"
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if "ERROR" in content:
                            display_name = f'<span style="color:{RED};">{CIRCLE}</span> {item}'  # Prefix warning symbol
                            item_contains_error = True
                        else:
                            display_name = f'<span style="color:{GREEN};">{CIRCLE}</span> {item}'
                    except Exception:
                        pass  # Ignore errors in file reading

                # If it's a directory, add a collapsible folder
                if os.path.isdir(full_path):
                    
                    sub_tree, sub_contains_error = build_tree(full_path)
                    if sub_contains_error:
                        triangle_style = f'"color:{RED};"'  # Mark directory if any file inside has "Error"
                        item_contains_error = True
                    else:
                        triangle_style = f'"color:{GREEN};"'
                    
                    html += f'<li class="folder" data-path="{unique_id}"><span class="toggle"><span id="triangle" style={triangle_style}>{TRIANGLE_RIGHT}</span><span> {item}</span></span>'
                    html += sub_tree
                    html += "</li>"
                else:
                    html += f'<li><a href="#" class="file-link" data-path="{relative_path}">{display_name}</a></li>'
                    
                # If any file or subdirectory contains "Error", mark the parent directory
                if item_contains_error:
                    directory_contains_error = True

            html += "</ul>"
            return html, directory_contains_error

        return f'''
            <h2>Mission Deployment Automation Logs</h2>
            <input type="text" id="search" placeholder="Search files...">
            {build_tree(base_path)[0]}
            '''
    

def main(server_class=HTTPServer, handler_class=CustomHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving on port {port}...")
    #os.system("open \"\" 'http://localhost:{}".format(port))
    httpd.serve_forever()
    

if __name__ == "__main__":
    main()
