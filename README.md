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
Edit the configuration file to add your email address. The plugin will send email-client tests and previews to that address.

On some occasions, the settings file is marked as read-only, depending on your installation and your OS. On OSX, that file is in `~/Library/Application\ Support/Sublime\ Text\ 3/Packages/triggermail_sublimetext_plugin/TriggerMail.sublime-settings` and you can make it writable by typing the following command in your terminal:

```
chmod 777 ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/triggermail_sublimetext_plugin/TriggerMail.sublime-settings
```


```
{
    /*
    URL of the TriggerMail engine.
     */
    "engine": "http://www.triggermail.io/",
    "preview_email": "mahmoud@triggermail.io",
    "products": {
        "query": "brief",
        "max": 10
    }
}
```

## Using the Plugin
There are three commands:

1. Preview the template in the browser
2. Send yourself a test version of the email.
3. Test the emails on a set of the most popular email clients. TriggerMail will email you back with screen shots of the template rendered within those clients.
