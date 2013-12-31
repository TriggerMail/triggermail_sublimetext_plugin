# Render & Test TriggerMail Templates in SublimeText

The plugin lets you edit and TriggerMail templates from within sublime. Usage goes something like this:

1. Edit the html. You can add inline CSS. TriggerMail inlines it for you at send or test time!
2. Hit save.
3. Issue a command to preview the template in your browser. You will see a rendered version of your template, complete with inlined CSS and REAL products from your site.

## Install the plugin
You can install the plugin directly from Github. See here for instructions:
http://www.macdrifter.com/2012/08/install-sublime-packages-from-github.html

## Edit the settings file
Press `Shift`+`Command`+`p` to get to the SublimeText command palette and pick `TriggerMail: open settings file`.
Edit the configuration file to add your email address. The plugin will send email tests and previews to that:

```
{
    /*
    URL of the engine
     */
    "engine": "http://www.triggermail.io/",
    "preview_email": "mahmoud@triggermail.io",
    "product_count": 4,
    /*
    The name of the partner
     */
    "partner": "tommy_john",
    "strategy": "RelatedProducts"
}
```

## Using the Plugin
There are three commands:

1. Preview the template in the browser
2. Send yourself a test version of the email.
3. Test the emails on a set of the most popular email clients. TriggerMail will email you back with screen shots of the template rendered within those clients.
