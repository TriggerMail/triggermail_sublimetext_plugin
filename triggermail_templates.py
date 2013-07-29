import sys
import os
import json
import webbrowser
import tempfile
import sublime, sublime_plugin
import webbrowser
import requests

try:
    settings = sublime.load_settings('TriggerMail.sublime-settings')
except:
    settings = {}


def read_file(filename):
    fh = open(filename, "r")
    contents = fh.read()
    fh.close()
    return contents

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

        print "Attempting to render %s for %s" % (action, partner)
        print "url is %s" % self.url
        request = requests.post(self.url, data=dict(templates=json.dumps(file_map), partner=partner, action=action, format="json"))
        response = request.text
        print response.text
        if request.status_code == 500:
            return sublime.error_message(request.json().get("message"))
        return response

class PreviewTemplate(_BasePreviewCommand):
    def run(self, edit):
        self.url = settings.get("engine", "http://www.triggermail.io/") + "api/templates/render_raw_template"
        response = super(PreviewTemplate, self).run(edit)
        # temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        # temp.write(response.encode("utf-8"))
        # temp.close()
        # webbrowser.open("file://"+temp.name)

class SendEmailPreview(_BasePreviewCommand) :
    def run(self, edit):
        self.url = settings.get("engine", "http://www.triggermail.io/") + "api/templates/render_to_email"
        super(SendEmailPreview, self).run(edit)
        self.view.set_status("trigger_mail", "Sent an email preview")
