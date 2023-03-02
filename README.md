<div>
<h1>OWASP BLT</h1>
</div>

[![Build Status](https://travis-ci.org/OWASP/BLT.svg?branch=master)](https://travis-ci.org/OWASP/BLT) 
<hr>

**Report issues and get points, companies are held accountable.** <br>
- OWASP BLT is a bug logging tool to report issues and get points, companies are held accountable. <br>
- Users will get rewards/points for reporting bugs on Organizations / Companies.<br>
- Organizations / Companies can launch their bughunt programs with prize pools. <br>

# Development
### Setting Up Development Server

Please follow the development server setup procedure [here](https://github.com/OWASP/BLT/blob/main/Setup.md). Currently, development server can be installed using docker or vagrant. You can also use virtualenv or pipenv install, pipenv shell and then continue with the remaining instructions.

### Documentation

- use the [Installation Docs ](https://github.com/OWASP/BLT/blob/main/Setup.md) to get started.
- Swagger API Documentations can be found at the root domain /swagger/
- Postman API Documentations:  [Postman Docs](https://documenter.getpostman.com/view/19782933/VUqpscyV).

### Resources

- Join the [OWASP Slack Channel](https://owasp.org/slack/invite) and ask questions at **#project-blt** 
- Github activity can be seen in Slack **#blt-github**.
- Figma designs for web and flutter app are available [here](https://www.figma.com/file/s0xuxeU6O2guoWEfA9OElZ/Design)


### Coding style guide

Please follow the [black](https://github.com/psf/black) code style for the project. It helps us in keeping the codebase consistent and improves readability for other developers.

### License
The BLT code is released under [GNU Affero General Public License v3.0 (AGPL-3.0)](https://github.com/OWASP/BLT/blob/master/LICENSE).

Why we chose AGPLv3 instead of MIT:

The main difference between the MIT license and the AGPLv3 (GNU Affero General Public License version 3) is their approach to the distribution of the source code and derivative works.

The MIT license is a permissive open-source license that allows anyone to use, modify, and distribute the software under certain conditions. The license allows the software to be used for commercial purposes, and it does not require the distribution of the source code or derivative works. Essentially, users can do whatever they want with the software as long as they include the original copyright and license notice in their derivative works.

On the other hand, the AGPLv3 is a copyleft open-source license that requires any user who modifies or distributes the software to distribute the source code of their modified version or derivative work under the same license terms. This license is designed to ensure that any user who modifies or distributes the software in a network environment (such as a web server) is required to share their changes with the community.

In summary, the main difference between the MIT license and the AGPLv3 is that the MIT license is permissive and allows users to use, modify, and distribute the software without distributing the source code or derivative works, while the AGPLv3 is a copyleft license that requires any user who modifies or distributes the software to distribute the source code of their modified version or derivative work under the same license terms.



## Notes

- If you find a bug or have an improvement, use BLT to report it!
- for each new issue, create a new branch with issue-382 or similar matching the issue number - when you commit add fixes #288 to link the issue to the pull request
- to take a github issue type a comment that says "assign to me" or /assign and it will assign it to you.
