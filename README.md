# Render & Test TriggerMail Templates in SublimeText

The plugin lets you edit and TriggerMail templates from within sublime. Usage goes something like this:

1. Edit the html. You can add inline CSS. TriggerMail inlines it for you at send or test time!
2. Hit save.
3. Issue a command to preview the template in your browser. You will see a rendered version of your template, complete with inlined CSS and REAL products from your site.

## Install the plugin
You can install the plugin directly from Github:
Press `Shift` + `Command` + `p` to get to the Sublime command palette and pick `Package Control: Add Repository`.
Paste the GitHub address for this repository: https://github.com/TriggerMail/triggermail_sublimetext_plugin/
`Shift` + `Command` + `p` and select `Package Control: Install Package`. You should now see the triggermail sublime text plugin.

* If these instructions do not work, try navigating to your packages folder and cloning this plugin directly into it. Then, open the settings file (as directed below) and change `use_cached` from true to false.

## Edit the settings file
Press `Shift`+`Command`+`p` to get to the SublimeText command palette and pick `TriggerMail: open settings file`.
Edit the configuration file to add your email address. The plugin will send email-client tests and previews to that address.

### If you can't edit the settings 

#### Read Only
On some occasions, the settings file is marked as read-only, depending on your installation and your OS. On OSX, that file is in `~/Library/Application\ Support/Sublime\ Text\ 3/Packages/triggermail_sublimetext_plugin/TriggerMail.sublime-settings` and you can make it writable by typing the following command in your terminal:

```
chmod 777 ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/triggermail_sublimetext_plugin/TriggerMail.sublime-settings
```

#### Directory not found
Sometimes that file won't save properly, which can be because the triggermail_sublimetext_plugin directory isn't created, you can create it with

```
mkdir ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/triggermail_sublimetext_plugin
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
Work on a template and then save it. There are three commands. You can execute any of them by pressing `command`+`shift`+`p`:

1. Preview the template in the browser
2. Send yourself a test version of the email.
3. Test the emails on a set of the most popular email clients. TriggerMail will email you back with screen shots of the template rendered within those clients.
