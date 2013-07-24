import sys
import os
import json
import webbrowser
import tempfile
import sublime, sublime_plugin
import webbrowser
import requests

try:
    settings = sublime.load_settings('TriggerMail_Templates.sublime-settings')
except:
    settings = {}


def read_file(filename):
    fh = open(filename, "r")
    contents = fh.read()
    fh.close()
    return contents

class PreviewTemplateCommand(sublime_plugin.TextCommand):
    def parse_partner_and_action(self):
        pass

    def run(self, edit):
        filename = self.view.file_name()
        print filename
        if not filename:
            sublime.error_message("You have to provide a template path.")

        if not os.path.exists(filename):
            sublime.error_message("File does not exist")
        path = os.path.dirname(filename)
        action = filename.replace(path, "").replace(".html", "").strip(os.sep)
        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        for root, dirs, files in os.walk(path):
            for filename in files:
                if filename.endswith(".html"):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents
        partner = path.split(os.sep)[-1]
        print "Attempting to render %s for %s" % (action, partner)
        request = requests.post(settings.get("engine"), data=dict(templates=json.dumps(file_map), partner=partner, action=action))
        response = request.text
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response.encode("utf-8"))
        temp.close()
        webbrowser.open("file://"+temp.name)