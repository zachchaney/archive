import os
import re
import datetime
import webbrowser
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.abspath('logs')
JAVASCRIPT = '/static/script.js?v=1.0.5'

# Symbols and colors
CIRCLE = '&#11044;'
TRIANGLE_DOWN = '&#9660;'
TRIANGLE_RIGHT = '&#9654;'

COLOR_SUCCESS = '#0BDA51'
COLOR_FAILURE = '#ff0000'
COLOR_RETRY = '#dddf02'
COLOR_UNKNOWN = '#cccccc'
COLOR_OVERRIDE = '#b47bf3'

# This needs to be ordered and dictionaries are only ordered in 3.7+
# We need to check for messages in a particular order and assign colors
message_colors = [("Override button pressed!", COLOR_OVERRIDE),
                   ("Command sent to retry failed job!", COLOR_RETRY),
                   ("FATAL:", COLOR_FAILURE),
                   ("Chef Run complete", COLOR_SUCCESS),
                   ("", COLOR_UNKNOWN)]
# The colors will bubble up given this priority
color_priority = [COLOR_UNKNOWN, COLOR_FAILURE, COLOR_OVERRIDE, COLOR_RETRY, COLOR_SUCCESS]


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
ANSI_ESCAPE_RE = re.compile(r'\[([1-9]+)(?:;(\d+))?(?:;(\d+))?m')

# Used as a unique identifier for JavaScript
initial_time = str(datetime.datetime.now())


def ansi_to_html(text):
    """Converts ANSI escape codes to HTML span elements."""
    def replace_ansi(match):
        codes = match.groups()
        styles = [ANSI_COLORS.get(code, "") for code in codes if code]
        return '<span style="{}">'.format(" ".join(styles))

    # Replace ANSI codes with styled <span> elements
    text = ANSI_ESCAPE_RE.sub(replace_ansi, text)

    # Close spans when the reset code \u001b[0m is found
    text = text.replace("[0m", "</span>")
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

        self.wfile.write("""
        <html>
        <head>
            <title>File Viewer</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
            <script src={} defer></script>
        </head>
        <body>
            <div class="sidebar">
                <div class="sidebar-header">
                    <div class="sidebar-title">Mission Deployment <br/>Automation Logs</div>
                    <div class="sidebar-search"><input type="text" id="search" placeholder="Search files..."></div>
                </div>
                <div class="sidebar-content">
                    {}
                </div>
                <div class="sidebar-key">
                    <span style="color:{};">{}</span> Unknown >
                    <span style="color:{};">{}</span> Failure ><br/>
                    <span style="color:{};">{}</span> Override >
                    <span style="color:{};">{}</span> Retry >
                    <span style="color:{};">{}</span> Success
                </div>
                <div class="resize-handle"></div>
            </div>
            <div class="content" id="content">
                <h2 class="file-title">Select a file</h2>
                <pre class="file-content">Click on a file to view its content.</pre>
            </div>
        </body>
        </html>
        """.format(JAVASCRIPT, sidebar_html, COLOR_UNKNOWN, CIRCLE, COLOR_FAILURE, CIRCLE, COLOR_OVERRIDE, CIRCLE, COLOR_RETRY, CIRCLE, COLOR_SUCCESS, CIRCLE).encode())
               

    def generate_sidebar(self, base_path):
        def build_tree(path, rel_path=""):
            items = sorted(os.listdir(path))  # Sort items alphabetically
            html = "<ul>"
            # dir_color_priority is the index in color_priority
            dir_color_priority = len(color_priority)-1
            
            for item in items:
                full_path = os.path.join(path, item)
                unique_id = full_path + initial_time # Unique identifier for JS
                relative_path = os.path.relpath(full_path, base_path)
                url_path = urllib.parse.quote(relative_path.replace("\\", "/"))
                
                display_name = item  # Default display name
                item_contains_error = False  # Track errors for this item
                item_color_priority = len(color_priority)-1

                # If it's a file, check for "Error"
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        for message in message_colors:
                            if message[0] in content:
                                file_color = message[1]
                                item_color_priority = min(item_color_priority, message_colors.index(message))
                                break
                        
                        display_name = '<span style="color:{};">{}</span> {}'.format(file_color, CIRCLE, item)
                        
                    except Exception:
                        pass  # Ignore errors in file reading

                # If it's a directory, add a collapsible folder
                if os.path.isdir(full_path):

                    sub_tree, sub_color_priority = build_tree(full_path)
                    
                    triangle_style = '"color:{};"'.format(color_priority[sub_color_priority])
                    
                    dir_color_priority = min(dir_color_priority, sub_color_priority)
                    
                    html += '<li class="folder" data-path="{}"><span class="toggle"><span id="triangle" style={}>{}</span><span> {}</span></span>'.format(unique_id, triangle_style, TRIANGLE_RIGHT, item)
                    html += sub_tree
                    html += "</li>"
                else:
                    html += '<li><a href="#" class="file-link" data-path="{}">{}</a></li>'.format(relative_path, display_name)
                    
                    # Keep in mind that item_color_priority is the index in message_color, we need to get the index in color_priority
                    dir_color_priority = min(dir_color_priority, color_priority.index(message_colors[item_color_priority][1]))

            html += "</ul>"
            return html, dir_color_priority

        return '''{}'''.format(build_tree(base_path)[0])
    

def main(server_class=HTTPServer, handler_class=CustomHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print("Serving on port {}...".format(port))
    webbrowser.open('http://localhost:{}'.format(port))
    httpd.serve_forever()
    

if __name__ == "__main__":
    main()
