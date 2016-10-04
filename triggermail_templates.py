from urllib.request import urlopen
import base64
import json
import os
import sublime, sublime_plugin
import logging
import tempfile
import urllib
import webbrowser

DEFAULT_USE_CACHE_SETTING = True
DEFAULT_AD_ACTION = 'window_shopping_ads'
DEFAULT_AD_CREATIVE_NAME = 'behavioral_ads'

def read_file(filename):
    fh = open(filename, "r", encoding="utf-8")
    contents = fh.read()
    fh.close()
    return contents

def is_integer(s):
    try:
        int(s)
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
    COMMAND_URL = ''

    def __init__(self, *args, **kwargs):
        self.settings = load_settings()
        super(_BasePreviewCommand, self).__init__(*args, **kwargs)

    def get_extra_params(self):
        return dict()

    def run(self, edit):
        self.url = get_url(self.settings) + self.COMMAND_URL
        use_pertinent_load = self.settings.get('pertinent_load', False)

        template_filename = self.view.file_name()
        if not template_filename:
            return sublime.error_message("You have to provide a template path.")
        if not template_filename.endswith(".html") and not template_filename.endswith(".txt"):
            return sublime.error_message("Invalid html template %s" % template_filename)
        if not os.path.exists(template_filename):
            return sublime.error_message("File does not exist")

        self.dissect_filename(template_filename)




        # get file names
        file_names = json.dumps(self.generate_file_list())
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)

        print("Attempting to render %s for %s" % (self.action, self.partner))
        print("url is %s" % self.url)

        params = dict(product_count=self.settings.get("product_count", 3),
                    partner=self.partner,
                    action=self.action,
                    format="json",
                    search_terms=json.dumps(self.settings.get("search_terms", [])),
                    products=json.dumps(self.settings.get("products")),
                    contents=json.dumps(self.settings.get("contents")),
                    customer_properties=json.dumps(self.settings.get("customer", {})),
                    canned_products=json.dumps(self.settings.get("canned_products", {})),
                    use_dev='dev.' in template_filename,
                    generation=getattr(self, 'generation', 0),
                    variant_id=getattr(self, 'variant_id', ''),
                    subaction=getattr(self, 'subaction', ''),
                    file_names=file_names)
        print(params)
        if not use_cache:
            params["templates"] = json.dumps(self.generate_file_map())
        try:
            nqe = self.settings.get("nqe")
            assert nqe
            params["nqe"] = nqe
        except:
            pass
        params.update(self.get_extra_params())
        # print(params)
        # request = urllib2.Request(self.url, urllib.urlencode(params))
        try:
            # response = urllib2.urlopen(request)
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            print(e)
            return str(e)
            # return str.encode(str(json.loads(e.read().decode("utf-8")).get("message")))

        return response.read()

    def dissect_filename(self, template_filename):
        self.path = os.path.dirname(template_filename)
        self.image_path = os.path.abspath(os.path.join(self.path, "img"))
        template_filename = template_filename.replace(self.path, '')

        url = get_url(self.settings) + "api/templates/dissect_filename"
        params = dict(template_filename=template_filename)
        response = urlopen(url, urllib.parse.urlencode(params).encode('utf-8'))
        result = response.read().decode('ascii')
        print(result)
        result = json.loads(result)
        for key, value in result.items():
            setattr(self, key, value)

        self.partner = self.path.split(os.sep)[-1]
        # You can override the partner in the settings file
        self.partner = self.settings.get("partner", self.partner) or self.partner
        self.partner = self.partner.replace("_templates", "")

    def generate_pertinent_file_names_and_map(self, template_filename):
        template_filename = template_filename.replace(self.path + '/', '')
        image_regex = "/img/" + self.partner + "/" + "(.*?)['\"]"
        file_map = dict()
        all_file_names_required = [template_filename]
        all_images_required = []
        # go through all files this template requires
        # we get all the filenames, their contents, and images
        for file_name in all_file_names_required:
            # some templates include html files that don't exist. Just because they don't exist, doesn't
            # mean it should automatically fail the command, they are most likely in jinja "if" statements
            try:
                contents = read_file(os.path.join(self.path, file_name))
            except:
                continue
            file_map[file_name] = contents
            # this regex finds all the other files the html file depends on. Because we're thenadding to
            # the loop we're cycling through, this can be recursive
            files_required_by_file = [file_name for _,file_name in \
                                        re.findall("{%\s*(include|extends|import)\s*['\"](.*?)['\"]", contents)]
            all_file_names_required += [x for x in files_required_by_file if x not in all_file_names_required]
            images_required_by_file = re.findall(image_regex, contents)
            all_images_required += [img for img in re.findall(image_regex, contents) if img not in all_images_required]

        for img in all_images_required:
            img_path = os.path.abspath(os.path.join(self.image_path, img))
            contents = encode_image(img_path)
            file_map[img] = contents

        all_file_names_required += all_images_required

        # lastly, we need to go through the other campaign files that accompany the html
        template_base_name = template_filename.split('.')[0]
        for postfix in ['.tracking', '.txt', '.yaml']:
            if postfix == '.txt':
                file_name = "_".join([self.action, "subject", self.subaction]) + postfix
            else:
                file_name = template_base_name+postfix
            try:
                all_file_names_required.append(file_name)
                contents = read_file(os.path.join(self.path, file_name))
                file_map[file_name] = contents
            except:
                sublime.error_message("trouble loading file " + file_name)

        return (all_file_names_required, file_map)

    def generate_file_map(self):
        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml', '.js']):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents

        # Read all the image files for this partner. Obviously, this is inefficient, and we should probably
        # only read the files that are used in the html file.
        # But we have no facilities for this kind of processing here, since it is a PITA to install pip
        # packages through a sublimetext plugin.
        # But we might have to figure this out if it becomes a performance bottleneck. I think it is ok
        # as long as you are on a fast connection.
        # image_path = os.path.abspath(os.path.join(self.path, "img"))

        for root, dirs, files in os.walk(self.image_path):
            for filename in files:
                image_path = os.path.abspath(os.path.join(root, filename))
                contents = encode_image(image_path)
                file_map[filename] = contents

        return file_map

    def generate_file_list(self):
        file_names = []
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml']):
                    file_names.append(filename)

        # self.image_path = os.path.abspath(os.path.join(self.path, "img"))

        for root, dirs, files in os.walk(self.image_path):
            for filename in files:
                # image_path = os.path.abspath(os.path.join(root, filename))
                file_names.append(filename)
        return file_names

class PreviewTemplate(_BasePreviewCommand):
    COMMAND_URL = "api/templates/render_plugin_template"

    def get_extra_params(self):
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)
        extra_params = dict(unique_user=os.environ['USER'] if use_cache else '')
        if use_cache:
            extra_params['templates'] = json.dumps({})
        return extra_params

    def run(self, edit):
        use_canned_blocks = self.settings.get('use_canned_blocks', False)
        if use_canned_blocks:
            self.COMMAND_URL = "api/templates/render_canned_blocks_plugin_template"

        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

class PreviewNamedTemplate(PreviewTemplate):

    COMMAND_URL = "api/templates/render_plugin_named_template"

    def dissect_filename(self, template_filename):
        self.path = os.path.dirname(template_filename)
        parts = template_filename.split('/')
        self.action = '/'.join(parts[-2:])
        self.action = self.action.replace('.html', '')
        print("my action: %s" % self.action)
        path = os.path.abspath(os.path.join(template_filename, os.pardir))
        self.parent_path = os.path.abspath(os.path.join(path, os.pardir))
        self.image_path = os.path.abspath(os.path.join(self.parent_path, "img"))
        self.partner = self.path.split(os.sep)[-1]
        # You can override the partner in the settings file
        self.partner = self.settings.get("partner", self.partner) or self.partner
        self.partner = self.partner.replace("_templates", "")

    def parse_file_name(self):
        # TODO: We need a more elegant way of doing this. Perhaps with regex
        template_filename = self.view.file_name()
        parts = template_filename.split('/')
        partner_name = parts[-3]
        print(partner_name)
        return dict(partner=partner_name, use_canned_products=True, use_random_canned_products=True)

    def generate_file_list(self):
        file_list = super(PreviewNamedTemplate, self).generate_file_list()
        parent_list = []
        print('parent path: %s' % self.parent_path)
        print('self path: %s' % self.path)
        for root, dirs, files in os.walk(self.parent_path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml']):
                    parent_list.append(filename)
        file_list.extend(parent_list)
        return file_list

    def generate_file_map(self):
        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        fdir = os.path.dirname(self.view.file_name()).replace(self.parent_path+'/', '')
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml', '.js']):
                    contents = read_file(os.path.join(root, filename))
                    file_map['%s/%s' % (fdir, filename)] = contents
                    # file_map[filename] = contents
        for root, dirs, files in os.walk(self.image_path):
            for filename in files:
                image_path = os.path.abspath(os.path.join(root, filename))
                contents = encode_image(image_path)
                file_map[filename] = contents
        for root, dirs, files in os.walk(self.parent_path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml', '.js']):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents
        print("my keys: %s" % file_map.keys())

        return file_map

    def get_extra_params(self):
        extra_params = super(PreviewNamedTemplate, self).get_extra_params()
        d = self.parse_file_name()
        extra_params.update(d)
        return extra_params

    def run(self, edit):
        use_auto_canned_blocks = self.settings.get('use_auto_canned_blocks', True)
        if use_auto_canned_blocks:
            self.COMMAND_URL = "api/templates/auto_canned_render_named_template"

        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

class PreviewEton(PreviewTemplate):
    COMMAND_URL = "eton/preview/"

    def get_extra_params(self):
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)
        extra_params = dict(unique_user=os.environ['USER'] if use_cache else '')
        if use_cache:
            extra_params['templates'] = json.dumps({})
        return extra_params

    def dissect_filename(self, template_filename):
        self.path = os.path.dirname(template_filename)
        self.image_path = os.path.abspath(os.path.join(self.path, "img"))
        template_filename = template_filename.replace(self.path, '')

        self.action = template_filename.replace(os.sep, '').replace('.html', '')
        self.partner = self.path.split(os.sep)[-1]
        # You can override the partner in the settings file
        self.partner = self.settings.get("partner", self.partner) or self.partner
        self.partner = self.partner.replace("_templates", "")

    def run(self, edit):
        template_filename = self.view.file_name()
        self.dissect_filename(template_filename)
        if not template_filename:
            return sublime.error_message("You have to provide a template path.")
        if not self.action.startswith("eton"):
            return sublime.error_message("Invalid eton template %s" % template_filename)
        if not os.path.exists(template_filename):
            return sublime.error_message("File does not exist")

        self.url = get_url(self.settings) + self.COMMAND_URL+self.partner+'/'+self.action.replace('eton_','')
        # get file names
        file_names = json.dumps(self.generate_file_list())
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)

        print("Attempting to render %s for %s" % (self.action, self.partner))
        print("url is %s" % self.url)

        params = dict(partner=self.partner,
                    action=self.action,
                    templates= json.dumps(self.generate_file_map()))
        try:
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            print(e)
            return str(e)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp.write(response.read())
        temp.close()
        webbrowser.open("file://"+temp.name)

class PreviewAdCreative(PreviewTemplate):

    COMMAND_URL = "api/templates/render_ad_creative"

    CREATIVE_LOADER = """
    <script language="Javascript1.1" type="text/javascript">
    function __write_preview(){
        // div = document.createElement("div"),
        div = document.getElementById("anchor"),
        frame = document.createElement('iframe');
        html = '__ad_creative_content_token__';
        // frame.src = 'data:text/html;charset=utf-8,' + html;
        div.id = 'testBcDiv';
        frame.id = 'testBcFrame';
        frame.width = __ad_creative_width_token__;
        frame.height = __ad_creative_height_token__;
        frame.frameBorder = 0;
        frame.scrolling = "no";
        frame.setAttribute('margin', '0');
        frame.setAttribute('allowTransparency', 'true');
        frame.setAttribute('allowTransparency', 'true');
        frame.setAttribute('webkitallowfullscreen','');
        frame.setAttribute('mozallowfullscreen','');
        frame.setAttribute('allowfullscreen','');
        // frame.setAttribute('style','background: #0066FF;');
        div.appendChild(frame);
        frame.contentWindow.document.open();
        frame.contentWindow.document.write(html);
        frame.contentWindow.document.close();
        // document.appendChild(div);
        /*
        if(!div.outerHTML) {
          iDiv = document.createElement('div');
          iDiv.appendChild(div);
          document.write(iDiv.innerHTML);
        } else {
          document.write(div.outerHTML);
        }
        */
    }
    var readyStateCheckInterval = setInterval(function() {
        if (document.readyState === "complete") {
            clearInterval(readyStateCheckInterval);
            __write_preview();
        }
    }, 10);
    </script>
    <html><div id="anchor"></html>
    """

    def dissect_filename(self, template_filename):
        response = super(PreviewAdCreative, self).dissect_filename(template_filename)
        path = os.path.abspath(os.path.join(template_filename, os.pardir))
        self.parent_path = os.path.abspath(os.path.join(path, os.pardir))
        self.image_path = os.path.abspath(os.path.join(self.parent_path, "img"))
        # print(self.image_path)
        return response

    def get_extra_params(self):
        extra_params = super(PreviewAdCreative, self).get_extra_params()
        d = self.parse_file_name()
        extra_params.update(d)
        action = self.settings.get('ads_action', DEFAULT_AD_ACTION)
        extra_params.update(dict(action=action))
        recipe_rules_path = '/src/%s/%s.yaml' % (self.partner, action)
        if os.path.exists(recipe_rules_path):
            recipe_rules_content = read_file(recipe_rules_path)
            extra_params['recipe_rules_file'] = recipe_rules_content
        else:
            logging.warn("Recipe rules file not found: %s" % recipe_rules_path)

        return extra_params

    def parse_file_name(self):
        # TODO: We need a more elegant way of doing this. Perhaps with regex
        template_filename = self.view.file_name()
        parts = template_filename.split('/')
        partner_name = parts[-3]
        parts = parts[-1]
        parts = parts.split('.')[0].split('_')
        if len(parts) < 3:
            message = "Error: You need a file size suffix in your file name"
            print(message)
            return sublime.error_message(message)
        size = '_'.join(parts[-2:])
        self.height = parts[-1]
        self.width = parts[-2]
        creative_name = '_'.join(parts[:-2])
        print(partner_name)
        return dict(size=size, creative_name=creative_name, partner=partner_name)

    def run(self, edit):
        ads_debug = self.settings.get('ads_debug', True)
        response = super(PreviewTemplate, self).run(edit)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        # print(response)
        if not ads_debug:
            response = response.decode('utf-8')
            response = response.replace("'", "\\'")
            response = response.replace('"', '\\"')
            response = response.replace('\n', '')
            # print(response)
            response = response.replace('</script>', '<\/script>')
            response = self.CREATIVE_LOADER.replace('__ad_creative_content_token__', response)
            response = response.replace('__ad_creative_width_token__', self.width)
            response = response.replace('__ad_creative_height_token__', self.height)
            response = response.encode('utf-8')
        temp.write(response)
        temp.close()
        webbrowser.open("file://"+temp.name)

    def generate_file_list(self):
        file_list = super(PreviewAdCreative, self).generate_file_list()
        parent_list = []
        for root, dirs, files in os.walk(self.parent_path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml']):
                    parent_list.append(filename)
        file_list.extend(parent_list)
        return file_list

    def generate_file_map(self):
        # Read all the files in the given folder.
        # We gather them all and then send them up to GAE.
        # We do this rather than processing template locally. Because local processing
        file_map = dict()
        fdir = os.path.dirname(self.view.file_name()).replace(self.parent_path+'/', '')
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml', '.js']):
                    contents = read_file(os.path.join(root, filename))
                    file_map['%s/%s' % (fdir, filename)] = contents
                    # file_map[filename] = contents
        for root, dirs, files in os.walk(self.image_path):
            for filename in files:
                image_path = os.path.abspath(os.path.join(root, filename))
                contents = encode_image(image_path)
                file_map[filename] = contents
        for root, dirs, files in os.walk(self.parent_path):
            for filename in files:
                if any(filename.endswith(postfix) for postfix in ['.tracking', '.html', '.txt', '.yaml', '.js']):
                    contents = read_file(os.path.join(root, filename))
                    file_map[filename] = contents
        print(file_map.keys())

        return file_map

class PreviewTemplateChannel(_BasePreviewCommand):
    COMMAND_URL = "plugin/start"

    def get_extra_params(self):
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)
        extra_params = dict(unique_user=os.environ['USER'] if use_cache else '')
        if use_cache:
            extra_params['templates'] = json.dumps({})
        return extra_params

    def run(self, edit):
        response = super(PreviewTemplateChannel, self).run(edit)
        # print(response)
        webbrowser.open(response.decode('utf-8'))

class SendEmailPreview(_BasePreviewCommand):
    COMMAND_URL = "api/templates/to_email_plugin_template"

    def get_extra_params(self):
        use_cache = self.settings.get('use_cache', DEFAULT_USE_CACHE_SETTING)
        extra_params = dict(email=self.settings.get("preview_email", ""), unique_user=os.environ['USER'] if use_cache else '')
        if use_cache:
            extra_params['templates'] = json.dumps({})
        return extra_params

    def run(self, edit):
        super(SendEmailPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent an email preview"))

class SendTestPreview(_BasePreviewCommand):
    COMMAND_URL = "api/templates/render_client_tests"

    def get_extra_params(self):
        return dict(email=self.settings.get("preview_email", ""))

    def run(self, edit):
        super(SendTestPreview, self).run(edit)
        print(self.view.set_status("trigger_mail", "Sent client test previews"))

class SendNamedTestPreview(PreviewNamedTemplate):

    COMMAND_URL = "api/templates/render_named_client_tests"

    def get_extra_params(self):
        res = super(SendNamedTestPreview, self).get_extra_params()
        res.update(dict(email=self.settings.get("preview_email", ""), cache_templates=False, unique_user=os.environ['USER']))
        return res

    def run(self, edit):
        use_auto_canned_blocks = self.settings.get('use_auto_canned_blocks', True)
        if use_auto_canned_blocks:
            self.COMMAND_URL = "api/templates/auto_canned_render_named_client_tests"
        _BasePreviewCommand.run(self, edit)
        print(self.view.set_status("trigger_mail", "Sent client test for named previews"))

class SendNamedEmailPreview(PreviewNamedTemplate):

    COMMAND_URL = "api/templates/forward_named_template"

    def get_extra_params(self):
        res = super(SendNamedEmailPreview, self).get_extra_params()
        res.update(dict(email=self.settings.get("preview_email", ""), cache_templates=False, unique_user=os.environ['USER']))
        return res

    def run(self, edit):
        use_auto_canned_blocks = self.settings.get('use_auto_canned_blocks', True)
        if use_auto_canned_blocks:
            self.COMMAND_URL = "api/templates/auto_canned_forward_named_template"
        _BasePreviewCommand.run(self, edit)
        print(self.view.set_status("trigger_mail", "Sent named previews"))

class ValidateYumli(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings)
        self.url += "api/yumli/validate_yumli"

        template_filename = self.view.file_name()
        self.path = os.path.dirname(template_filename)

        self.partner = self.path.split(os.sep)[-1]
        # You can override the partner in the settings file
        self.partner = settings.get("partner", self.partner) or self.partner
        print("Attempting to validate for %s" % (self.partner))
        self.partner = self.partner.replace("_templates","")

        recipe_rules_file = self.view.file_name()
        if not recipe_rules_file:
            return sublime.error_message("You have to provide a template path.")
        if not recipe_rules_file.endswith(".yaml"):
            return sublime.error_message("Not a YAML file: %s" % recipe_rules_file)
        if not os.path.exists(recipe_rules_file):
            return sublime.error_message("File does not exist")

        # send the contents of the file
        params = dict(
            yumli_file=read_file(recipe_rules_file),
            partner=self.partner,
            file_name=recipe_rules_file
        )

        try:
            urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            error = e.read().decode("utf-8")
            print(error)
            if hasattr(e, "read"):
                try:
                    return sublime.error_message(str(json.loads(error).get("text")))
                except:
                    pass
            return sublime.error_message(str(e))
        return sublime.message_dialog('YAYYY Valid!')


class KeenFunnels(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = load_settings()
        self.url = get_url(settings) + "api/customers/run_funnel"

        content = self.view.substr(sublime.Region(0, self.view.size()))
        params = dict(payload=content)
        try:
            response = urlopen(self.url, urllib.parse.urlencode(params).encode("utf-8"))
        except urllib.error.URLError as e:
            print(e)
            if hasattr(e, "read"):
                return sublime.error_message(str(json.loads(e.read().decode("utf-8")).get("message")))
            return sublime.error_message(str(e))
        content = response.read().decode("utf-8")
        print(content)
        view = make_new_view(self.view.window(), content, scratch=True)
        view.set_syntax_file("Packages/YAML/YAML.tmLanguage")

def make_new_view(window, text, scratch=False):
    """ create a new view and paste text content
        return the new view.
        Optionally can be set as scratch.
    """

    new_view = window.new_file()
    if scratch:
        new_view.set_scratch(True)
    new_view.run_command('append', {
            'characters': text,
        })
    return new_view
