from urllib.request import urlopen
import base64
import json
import os
import sublime, sublime_plugin
import tempfile
import urllib
import webbrowser

DEFAULT_USE_CACHE_SETTING = False
ACTIONS = ['window_shopping', 'abandoned_cart', 'abandoned_search', 'post_purchase', 'welcome']

def read_file(filename):
    fh = open(filename, "r", encoding="utf-8")
    contents = fh.read()
    fh.close()
    return contents

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def encode_image(filename):
    """ Base64 encodes an image so that we can embed it in the html.
    """
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string.decode("utf-8")

def load_settings():
    return sublime.load_settings('TriggerMail.sublime-settings')

def get_url(settings):
    try:
        return settings.get("engine", "http://www.triggermail.io/")
    except TypeError:
        return "http://www.triggermail.io/"

class _BasePreviewCommand(sublime_plugin.TextCommand):
    url = None
    encode_images = True

    def get_extra_params(self):
        return dict()

    def run(self, edit):
        settings = load_settings()
        template_filename = self.view.file_name()
        if not template_filename:
            return sublime.error_message("You have to provide a template path.")
        if not template_filename.endswith(".html") and not template_filename.endswith(".txt"):
            return sublime.error_message("Invalid html template %s" % template_filename)
        if not os.path.exists(template_filename):
            return sublime.error_message("File does not exist")

        self.dissect_filename(template_filename, settings)

        # Read all the partner assets files
        if settings.get('use_cache', DEFAULT_USE_CACHE_SETTING):
            file_map = {}
        else:
            file_map = self.generate_file_map()

        print("Attempting to render %s for %s" % (self.action, self.partner))
        print("url is %s" % self.url)

        params = dict(product_count=settings.get("product_count", 3),
                    templates=json.dumps(file_map),
                    partner=self.partner,
                    action=self.action,
                    format="json",
                    search_terms=json.dumps(settings.get("search_terms", [])),
                    products=json.dumps(settings.get("products")),
                    customer_properties=json.dumps(settings.get("customer", {})),
                    use_dev='dev.' in template_filename,
                    generation=self.generation,
                    variant_id=self.variant_id)
        print(params.get("customer_properties"))
        try:
            cpn = settings.get("cpn")
            assert cpn
            params["cpn"] = cpn
        except:
            pass
        params.update(self.get_extra_params())

        # request = urllib2.Request(self.url, urllib.urlencode(params))
        try:
            # response = urllib2.urlopen(request)
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            if hasattr(e, "read"):
                return sublime.error_message(json.loads(e.read().decode("utf-8")).get("message"))
            return sublime.error_message(str(e))
        return response.read()

    def dissect_filename(self, template_filename, settings):
        self.path = os.path.dirname(template_filename)
        self.action = template_filename.replace(self.path, "").replace(".html", "").replace('dev.', '').strip(os.sep)
        self.generation = 0
        self.variant_id = 'default'
        path_parts = self.action.split("_")
        if all([is_number(part) for part in path_parts[-2:]]):
            self.generation = path_parts[-1]
            self.variant_id = "_".join(path_parts[-3:-1])
            self.action = "_".join(path_parts[:-3])
        elif is_number(path_parts[-1]) and "variant" in path_parts:
            self.variant_id = "_".join(path_parts[-2:])
            self.action = "_".join(path_parts[:-2])
        elif is_number(path_parts[-1]):
            self.generation = path_parts[-1]
            self.action = "_".join(path_parts[:-1])
        print('generation: %s' % self.generation)
        print('variant: %s' % self.variant_id)
        print('action: %s' % self.action)

        self.partner = self.path.split(os.sep)[-1]
        # You can override the partner in the settings file
        self.partner = settings.get("partner", self.partner) or self.partner
        self.partner = self.partner.replace("_templates", "")

    def generate_file_map(self):
        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if filename.endswith(".tracking") or filename.endswith(".html") or filename.endswith(".txt") or filename.endswith(".yaml"):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents

        # Read all the image files for this partner. Obviously, this is inefficient, and we should probably
        # only read the files that are used in the html file.
        # But we have no facilities for this kind of processing here, since it is a PITA to install pip
        # packages through a sublimetext plugin.
        # But we might have to figure this out if it becomes a performance bottleneck. I think it is ok
        # as long as you are on a fast connection.
        image_path = os.path.abspath(os.path.join(self.path, "img"))

        if self.encode_images:
            for root, dirs, files in os.walk(image_path):
                for filename in files:
                    image_path = os.path.abspath(os.path.join(root, filename))
                    contents = encode_image(image_path)
                    file_map[filename] = contents

        return file_map

class PreviewTemplate(_BasePreviewCommand):
    def get_extra_params(self):
        settings = load_settings()
        use_cache = settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)
        return dict(unique_user=os.environ['USER'] if use_cache else '')

    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings)
        self.url += "api/templates/render_raw_template"

        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

class SendEmailPreview(_BasePreviewCommand):
    encode_images = False
    def get_extra_params(self):
        settings = load_settings()
        return dict(email=settings.get("preview_email", ""))

    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings)
        self.url += "api/templates/render_to_email"

        super(SendEmailPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent an email preview"))

class SendTestPreview(_BasePreviewCommand):
    encode_images = False
    def get_extra_params(self):
        settings = load_settings()
        return dict(email=settings.get("preview_email", ""))

    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings)
        self.url += "api/templates/render_client_tests"

        super(SendTestPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent client test previews"))

class ValidateRecipeRulesFile(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings)
        self.url += "api/templates/validate_recipe_rules_file"

        recipe_rules_file = self.view.file_name()
        if not recipe_rules_file:
            return sublime.error_message("You have to provide a template path.")
        if not recipe_rules_file.endswith(".yaml"):
            return sublime.error_message("Not a YAML file: %s" % recipe_rules_file)
        if not os.path.exists(recipe_rules_file):
            return sublime.error_message("File does not exist")

        # send the contents of the file
        params = dict(
            recipe_rules_file=read_file(recipe_rules_file),
        )

        try:
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            if hasattr(e, "read"):
                return sublime.error_message(json.loads(e.read().decode("utf-8")).get("message"))
            return sublime.error_message(str(e))
        return sublime.message_dialog('YAYYY Valid!')



