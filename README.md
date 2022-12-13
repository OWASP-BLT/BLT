
<div style="display:flex;">
	<img align="right" src="https://avatars.githubusercontent.com/u/20373732?s=200&v=4" alt="logo" width="80px" />
	# [OWASP BLT](https://www.bugheist.com) [![Build Status](https://travis-ci.org/OWASP/BLT.svg?branch=master)](https://travis-ci.org/OWASP/BLT) 
</div>

<hr>

**Report issues and get points, companies are held accountable.** <br>
- OWASP BLT is a bug logging tool to report issues and get points, companies are held accountable. <br>
- Users will get rewards/points for reporting bugs on Organizations / Companies.<br>
- Organizations / Companies can launch their bughunt programs with prize pools. <br>


## Bugheist Bug Reporting Plugin

A floating bug reporting button for your website which redirects back to Bugheist and help's users to report bug for that specific page. Just embed this script within body tag of your page to enable this plugin.

  ```
    <script type="text/javascript">
		var button = document.createElement("Button");
		button.style = "bottom:15px;left:15px;position:fixed;z-index: 12;border-radius:100%;background: url('https://www.bugheist.com/static/img/logo.0cc160e97934.png') no-repeat center; height: 50px; width: 50px; outline: none;background-size: 50px 50px;"
		document.body.appendChild(button);
		var url = window.location.href;
		var bugheist = 'https://www.bugheist.com/report/?url=' + url;
		button.onclick = function() {
			var redirectWindow = window.open(bugheist, '_blank');
            redirectWindow.location;
		}
	</script>
  ```

# Development
### Setting Up Development Server

Please follow the development server setup procedure [here](https://github.com/OWASP/BLT/blob/main/Setup.md). Currently, development server can be installed using docker or vagrant. You can also use virtualenv or pipenv install, pipenv shell and then continue with the remaining instructions.

### Documentation

- use the [Installation Docs ](https://github.com/OWASP/BLT/blob/main/Setup.md) to get started.
- Postman API Documentations are available [Here](https://github.com/OWASP/BLT/blob/main/Setup.md).

### Resources

- Join the [OWASP Slack Channel](https://owasp.org/slack/invite) and ask questions at **#project-blt** 
- Github activity can be seen in Slack **#blt-github**.
- Figma designs for web and flutter app are available [here](https://www.figma.com/file/s0xuxeU6O2guoWEfA9OElZ/Bugheist-Full-Design)
- Live Site: [Bugheist.com](https://www.bugheist.com/)
- Project: [Bugheist Org](https://github.com/Bugheist)


### Coding style guide

Please follow the [black](https://github.com/psf/black) code style for the project. It helps us in keeping the codebase consistent and improves readibility for other developers.

### License

The BLT code is released under [GNU Affero General Public License v3.0 (AGPL-3.0)](https://github.com/OWASP/BLT/blob/master/LICENSE.md).


## Mobile App
BLT mobile version codebase which is built in Flutter is available at [BLT Flutter](https://github.com/Bugheist/Flutter).


## Notes

- If you find a bug or have an improvement, use BLT to report it!
- Our staging server is at https://bugheist-staging.herokuapp.com/ - staging uses the master branch and we have review apps setup that deploy a new instance for each pull request. 
- for each new issue, create a new branch with issue-382 or similar matching the issue number - when you commit add fixes #288 to link the issue to the pull request
- Our Figma desins are also Open Source you can see them here https://www.figma.com/file/s0xuxeU6O2guoWEfA9OElZ/Bugheist-Full-Design to contribute to the design, add a pull request to the design changes file and we will merge them into our main figma file.
- to take a github issue type a comment that says "assign to me" and it will assign it to you.
