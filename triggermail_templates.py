import sys
import os
import json
import webbrowser
import tempfile
import sublime, sublime_plugin
import webbrowser
import urllib, urllib2
import base64
try:
    settings = sublime.load_settings('TriggerMail.sublime-settings')
except:
    settings = {}


def read_file(filename):
    fh = open(filename, "r")
    contents = fh.read()
    fh.close()
    return contents

def encode_image(filename):
    """ Base64 encodes an image so that we can embed it in the html.
    """
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string

class _BasePreviewCommand(sublime_plugin.TextCommand):
    url = None
    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            return sublime.error_message("You have to provide a template path.")
        if not filename.endswith(".html"):
            return sublime.error_message("Invalid html template %s" % filename)
        if not os.path.exists(filename):
            return sublime.error_message("File does not exist")

        # Read all the HTML files
        path = os.path.dirname(filename)
        action = filename.replace(path, "").replace(".html", "").strip(os.sep)
        partner = path.split(os.sep)[-1]
        # You can override the partner in the settings file
        partner = settings.get("partner", partner) or partner

        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        for root, dirs, files in os.walk(path):
            for filename in files:
                if filename.endswith(".html") or filename.endswith(".txt"):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents

        # Read all the image files for this partner. Obviously, this is inefficient, and we should probably
        # only read the files that are used in the html file.
        # But we have no facilities for this kind of processing here, since it is a PITA to install pip
        # packages through a sublimetext plugin.
        # But we might have to figure this out if it becomes a performance bottleneck. I think it is ok
        # as long as you are on a fast connection.
        image_path = os.path.join(path, "..", "..", "..", "..", "static", "img", partner)
        print os.path.abspath(image_path)
        for root, dirs, files in os.walk(image_path):
            for filename in files:
                contents = encode_image(os.path.join(root, filename))
                file_map[filename] = contents

        print "Attempting to render %s for %s" % (action, partner)
        print "url is %s" % self.url
        print file_map.keys()

        params = dict(templates=json.dumps(file_map), partner=partner, action=action, format="json")
        request = urllib2.Request(self.url, urllib.urlencode(params))
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            if hasattr(e, "read"):
                return sublime.error_message(json.loads(e.read()).get("message"))
            return sublime.error_message(str(e))
        return response.read()

class PreviewTemplate(_BasePreviewCommand):
    def run(self, edit):
        self.url = settings.get("engine", "http://www.triggermail.io/") + "api/templates/render_raw_template"
        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

class SendEmailPreview(_BasePreviewCommand) :
    def run(self, edit):
        self.url = settings.get("engine", "http://www.triggermail.io/") + "api/templates/render_to_email"
        super(SendEmailPreview, self).run(edit)
        self.view.set_status("trigger_mail", "Sent an email preview")
