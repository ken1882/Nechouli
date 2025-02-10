Deploy:
  Git:
    # URL of AzurLaneAutoScript repository
    # [CN user] Use 'cn' to get update from git-over-cdn service
    # [Other] Use 'global' to get update from https://github.com/ken1882/Nechouli
    Repository: {{repository}}
    # Branch of Alas
    # [Developer] Use 'dev', 'app', etc, to try new features
    # [Other] Use 'main', the stable branch
    Branch: main
    # Filepath of git executable `git.exe`
    # [Easy installer] Use './toolkit/Git/mingw64/bin/git.exe'
    # [Other] Use you own git
    GitExecutable: {{gitExecutable}}
    # Set git proxy
    # [CN user] Use your local http proxy (http://127.0.0.1:{port}) or socks5 proxy (socks5://127.0.0.1:{port})
    # [Other] Use null
    GitProxy: null
    # Set SSL Verify
    # [In most cases] Use true
    # [Other] Use false to when connected to an untrusted network
    SSLVerify: true
    # Update Alas at startup
    # [In most cases] Use true
    AutoUpdate: true
    # Whether to keep local changes during update
    # User settings, logs and screenshots will be kept, no mather this is true or false
    # [Developer] Use true, if you modified the code
    # [Other] Use false
    KeepLocalChanges: false

  Python:
    # Filepath of python executable `python.exe`
    # [Easy installer] Use './toolkit/python.exe'
    # [Other] Use you own python, and its version should be 3.7.6 64bit
    PythonExecutable: {{pythonExecutable}}
    # URL of pypi mirror
    # [CN user] Use 'https://pypi.tuna.tsinghua.edu.cn/simple' for faster and more stable download
    # [Other] Use null
    PypiMirror: null
    # Install dependencies at startup
    # [In most cases] Use true
    InstallDependencies: true
    # Path to requirements.txt
    # [In most cases] Use 'requirements.txt'
    # [In AidLux] Use './deploy/AidLux/{version}/requirements.txt', version is default to 0.92
    RequirementsFile: requirements.txt

  Adb:
    # Filepath of ADB executable `adb.exe`
    # [Easy installer] Use './toolkit/Lib/site-packages/adbutils/binaries/adb.exe'
    # [Other] Use you own latest ADB, but not the ADB in your emulator
    AdbExecutable: {{adbExecutable}}
    # Whether to replace ADB
    # Chinese emulators (NoxPlayer, LDPlayer, MemuPlayer, MuMuPlayer) use their own ADB, instead of the latest.
    # Different ADB servers will terminate each other at startup, resulting in disconnection.
    # For compatibility, we have to replace them all.
    # This will do:
    #   1. Terminate current ADB server
    #   2. Rename ADB from all emulators to *.bak and replace them by the AdbExecutable set above
    #   3. Brute-force connect to all available emulator instances
    # [In most cases] Use true
    # [In few cases] Use false, if you have other programs using ADB.
    ReplaceAdb: true
    # Brute-force connect to all available emulator instances
    # [In most cases] Use true
    AutoConnect: true
    # Re-install uiautomator2
    # [In most cases] Use true
    InstallUiautomator2: true

  Ocr:
    # Run Ocr as a service, can reduce memory usage by not import mxnet everytime you start an alas instance

    # Whether to use ocr server
    # [Default] false
    UseOcrServer: false
    # Whether to start ocr server when start GUI
    # [Default] false
    StartOcrServer: false
    # Port of ocr server runs by GUI
    # [Default] 22268
    OcrServerPort: 22268
    # Address of ocr server for alas instance to connect
    # [Default] 127.0.0.1:22268
    OcrClientAddress: 127.0.0.1:22268

  Update:
    # Use auto update and builtin updater feature
    # This may cause problem https://github.com/LmeSzinc/AzurLaneAutoScript/issues/876
    EnableReload: true
    # Check update every X minute
    # [Disable] 0
    # [Default] 5
    CheckUpdateInterval: 5
    # Scheduled restart time
    # If there are updates, Alas will automatically restart and update at this time every day
    # and run all alas instances that running before restarted
    # [Disable] null
    # [Default] 03:50
    AutoRestartTime: 03:50

  Misc:
    # Enable discord rich presence
    DiscordRichPresence: false

  RemoteAccess:
    # Enable remote access (using ssh reverse tunnel serve by https://github.com/wang0618/localshare)
    # ! You need to set Password below to enable remote access since everyone can access to your alas if they have your url.
    # See here (http://app.azurlane.cloud/en.html) for more infomation.
    EnableRemoteAccess: false
    # Username when login into ssh server
    # [Default] null (will generate a random one when startup)
    SSHUser: null
    # Server to connect
    # [Default] null
    # [Format] host:port
    SSHServer: null
    # Filepath of SSH executable `ssh.exe`
    # [Default] ssh (find ssh in system PATH)
    # If you don't have one, install OpenSSH or download it here (https://github.com/PowerShell/Win32-OpenSSH/releases)
    SSHExecutable: ssh

  Webui:
    # --host. Host to listen
    # [Use IPv6] '::'
    # [In most cases] Default to '0.0.0.0'
    WebuiHost: 0.0.0.0
    # --port. Port to listen
    # You will be able to access webui via `http://{host}:{port}`
    # [In most cases] Default to 22367
    WebuiPort: 22367
    # Language to use on web ui
    # 'zh-CN' for Chinese simplified
    # 'en-US' for English
    # 'ja-JP' for Japanese
    # 'zh-TW' for Chinese traditional
    # 'es-ES' for Spanish
    Language: {{language}}
    # Theme of web ui
    # 'default' for light theme
    # 'dark' for dark theme
    Theme: {{theme}}
    # Follow system DPI scaling
    # [In most cases] true
    # [In few cases] false to make Alas smaller, if you have a low resolution but high DPI scaling.
    DpiScaling: true
    # --key. Password of web ui
    # Useful when expose Alas to the public network
    Password: null
    # --cdn. Use jsdelivr cdn for pywebio static files (css, js).
    # 'true' for jsdelivr cdn
    # 'false' for self host cdn (automatically)
    # 'https://path.to.your/cdn' to use custom cdn
    CDN: false
    # --run. Auto-run specified config when startup
    # 'null' default no specified config
    # '["alas"]' specified "alas" config
    # '["alas","alas2"]' specified "alas" "alas2" configs
    Run: null
    # To update app.asar
    # [In most cases] true
    AppAsarUpdate: true
    # --no-sandbox. https://github.com/electron/electron/issues/30966
    # Some Windows systems cannot call the GPU normally for virtualization, and you need to manually turn off sandbox mode
    NoSandbox: false
