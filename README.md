This application allows you to start a specific working environment, opening the applications 
you need and placing them at the desired screen locations.

It is controlled by an INI config file, specified as follows
	--config-file="full_pathname"
	
Here is the full list of command line switches:
--config-file		Full pathname of the config file. This is required.

The following are optional
--show-debug-info		Show debug info
--no-debug-info			Do not show debug info
--dry-run				Show info on what would happen but do not take any action
--no-dry-run			This is a real run!


The config file is made up of the following 4 sections
1- Variable definition
2- 'before' apps.
3- 'after' apps
4- browser definition

Note: When the app was originally written, it was used to start up a web development environment on the local PC.
This meant that, at some point, the MYSQL server would be started up.
Rather than wait for it to start up, apps that did not need it would be started in the 'before' phase.
However apps that needed it, such as Sql editors etc, would need to wait till it was started.
One Mysql was started up, the 'after' apps were launched.

Since this app is now intended for a more general use, this has now been renamed to 'before' and 'after' apps.
The app that is in between the 'before' and 'after' apps is called the 'barrier' app.
If you are not using a barrier app then no checks will be done and the 'after' section will be run right after the 'before' section.
Simply leave the 'barrier' app name blank.

In addition to the barrier app, there is provision for an optional barrier service.
If its name ('barrier_service_name') is not blank then the app will wait for it to start, i.e. its EXE to be running.
It is expected that this service is started by the barrier app.
In short:
	If the barrier app name ('barrier_app') is not blank, make sure it is running. Start it and wait if not.
		If the barrier service name ('barrier_service_name')  is not blank, wait until it is up and running.


An example config file ('00-setup-work-env.ini') is shown below.


```
[default]
; lines starting with a ';' are comment lines

; defines various variables that will be used further down. 
; Note that the 5 shown below are all required, since the code actually looks for them.
work_dir=w:\work\php\Laravel\proj
barrier_app=app1.exe
barrier_service_name=

# this can be used in variable expansion in titles etc. 
app_name=MyApp
browser=firefox_dev
browser_title=Home page - App1

; The app handles url - url4. Additionally, url may contain '$appName' will will be replaced with the app name. Beware of spaces in the app name!
url=http://app1.local
url2=
url3=
url4=

; You can have your own variables here...(Position is not important. You can have the apps defined in any order, so long
; as the 4 above 'url' variables are actually defined.
;
;

; Line format
appxx=config options
where xx is a running number. See below

; config options format: 	(the following are separated by ' ~ ')
; The number shown below is for convenience only...
;	0		appPath			Full pathname of app to run
;	1		appTitle		If it starts with '*' then a 'contains' match is used. '*' is only needed in the 1st char of the title!
;	2		x,y,w,h			x, y, width and height of the created app's window. 
;	3		params			Params for the app to be launched
;	4		minimised		yes/no
;	5		before_start_delay,after_start_delay		optional delays, in seconds, to use before/after the app is launched
;	6		app2waitForPathname,app2waitForTitle		optional app to wait for and the window title to look for.
[before]
app0=C:\Windows\Notepad.exe
app1=w:\NetBeans\NetBeans-29\bin\netbeans64.exe ~ *Apache NetBeans ~ 575, 5, 1950, 1350 ~ "${workDir}" --console suppress --userdir "${workDir}/netbeans" ~ no
; open browser with 4 URLs, not minimised
app2=${browser} ~ *${browser_title} ~ 2565, -700, 1800, 1500 ~ --new-window ${url} ${url2} ${url3} ${url4}~ no
app3=C:\Program Files\ConEmu\ConEmu64.exe ~ Artisan ~ 1665,955,900,450 ~ -Title "Artisan" -dir "${workDir}" ~ yes
; open Windows Explorer in the working directory
app4=explorer ~ ${app_name} ~ 1450, 630, 1050, 775 ~ "${workDir}" ~ yes
; etc

[after]
app0=C:\Program Files\SQLyog\SQLyog.exe ~ *SQLyog ~ 3350, 300, 2100, 1080 ~ ~ yes
app1=${browser} ~ *${browser_title} ~ 2565, -700, 1800, 1500 ~ --new-window ${url} ~ no
app2=${workDir}\00 file watcher.bat ~ File watcher ~ 5135, 795, 1270, 620 ~ ~ no
; etc

[browsers]
brave=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
chrome=C:\Program Files\Google\Chrome\Application\chrome.exe
firefox=w:\Portable Apps\LiberKey\MyApps\FirefoxPortable\FirefoxPortable.exe
firefox_dev=C:\Program Files\Firefox Developer Edition\firefox.exe
edge=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
blisk=C:\Users\fred\AppData\Local\Blisk\Application\blisk.exe

```
'click' library
=============
The 'click' library is used to manage the command-line parameters.
It takes over the startup code and provides the following function as the **app entry point**, i.e. this is where your 
code gets once click has sorted out the command-line parameters.
The @click.option lines define each expected parameter and its type (default is str or click.STRING)

the 'def main()' line then starts the definition of the 'main' function and it is passed all the parameters defined above.

```
@click.command()
@click.option("--show-debug-info/--no-debug-info", default=False)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--config-file", type=str)
def main(show_debug_info: bool, dry_run: bool, config_file: str) -> None:
```



Colorama.Style library
======================
