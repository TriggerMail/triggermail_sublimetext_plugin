from urllib.request import urlopen
import base64
import codecs
import json
import os
import sublime, sublime_plugin
import tempfile
import urllib
import webbrowser
# try:
settings = sublime.load_settings('TriggerMail.sublime-settings')
# except:
    # settings = {}


def read_file(filename):
    fh = open(filename, "r", encoding="utf-8")
    contents = fh.read()
    fh.close()
    return contents

def encode_image(filename):
    """ Base64 encodes an image so that we can embed it in the html.
    """
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string.decode("utf-8")

class _BasePreviewCommand(sublime_plugin.TextCommand):
    url = None
    def get_extra_params(self):
        return dict()

    def run(self, edit):
        template_filename = self.view.file_name()
        if not template_filename:
            return sublime.error_message("You have to provide a template path.")
        if not template_filename.endswith(".html") and not template_filename.endswith(".txt"):
            return sublime.error_message("Invalid html template %s" % template_filename)
        if not os.path.exists(template_filename):
            return sublime.error_message("File does not exist")

        # Read all the HTML files
        path = os.path.dirname(template_filename)
        action = template_filename.replace(path, "").replace(".html", "").replace('dev.', '').strip(os.sep)
        generation = 0
        if action[-1] in '0123456789':
            generation = action.split('_')[-1]
            action = '_'.join(action.split('_')[:-1])
        partner = path.split(os.sep)[-1]
        # You can override the partner in the settings file
        partner = settings.get("partner", partner) or partner
        partner = partner.replace("_templates", "")

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
        image_path = os.path.abspath(os.path.join(path, "..", "..", "..", "..", "static", "img", partner))

        if not os.path.exists(image_path):
            # For when the templates are in a separate repo.
            image_path = os.path.abspath(os.path.join(path, "img", partner))

        for root, dirs, files in os.walk(image_path):
            for filename in files:
                image_path = os.path.abspath(os.path.join(root, filename))
                print(image_path)
                contents = encode_image(image_path)
                print(contents)
                file_map[filename] = contents

        print("Attempting to render %s for %s" % (action, partner))
        print("url is %s" % self.url)

        params = dict(product_count=settings.get("product_count", 3),
                    templates=json.dumps(file_map),
                    partner=partner,
                    action=action,
                    format="json",
                    cpn=settings.get("cpn", ""),
                    strategy=settings.get('strategy', None),
                    strategy_kwargs=settings.get('strategy_kwargs', {}),
                    use_dev='dev.' in template_filename,
                    generation=generation)
        params.update(self.get_extra_params())

        # request = urllib2.Request(self.url, urllib.urlencode(params))
        try:
            # response = urllib2.urlopen(request)
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            if hasattr(e, "read"):
                print(e)
                return sublime.error_message(json.loads(e.read().decode("utf-8")).get("message"))
            return sublime.error_message(str(e))
        return response.read()

class PreviewTemplate(_BasePreviewCommand):
    def run(self, edit):
        self.url = ""
        try:
            self.url += settings.get("engine", "http://www.triggermail.io/")
        except TypeError:
            self.url = "http://www.triggermail.io/"
        self.url += "api/templates/render_raw_template"

        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

class SendEmailPreview(_BasePreviewCommand):
    def get_extra_params(self):
        return dict(email=settings.get("preview_email", ""))

    def run(self, edit):
        self.url = ""
        try:
            self.url += settings.get("engine", "http://www.triggermail.io/")
        except TypeError:
            self.url = "http://www.triggermail.io/"
        self.url += "api/templates/render_to_email"

        super(SendEmailPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent an email preview"))

class SendTestPreview(_BasePreviewCommand):
    def get_extra_params(self):
        return dict(email=settings.get("preview_email", ""))

    def run(self, edit):
        self.url = ""
        try:
            self.url += settings.get("engine", "http://www.triggermail.io/")
        except TypeError:
            self.url = "http://www.triggermail.io/"
        self.url += "api/templates/render_client_tests"

        super(SendTestPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent client test previews"))

