Buildly is a continuous build system for building iOS apps. It watches the designated branches of a git repository and if the app version number changes in a branch a new build for that branches configuration is kicked off.

Buildly is capable of changing the app's display name, icons, re-codesigning the app, pushing to HockeyApp with auto generated release notes for any commit message line that begins with a `-`, and much more via scripting hooks.

Buildly was architected in a modular structure and there are several layers. Only the configuration layer should need to be customized to build your app, but all layers will be discussed in this document.

Buildly is run from the command line with the following command:

```
python buildly.py <path to buildly.plist>
```

Running this will cause Buildly to checkout the specified branch for each build configuration. Every 10 minutes the repositories are updated and if the app version number has changed since the last build a new build is kicked off.

# buildly.plist

This is the configuration file that contains all of the information needed for the build system and the various builds you want to do. The file does not have to be named `buildly.plist` it is just recommend and will be referred to by this name later in this document.

An example plist named `example_buildly.plist` is included in this repository that can be used as a starting point.

There are several global keys:

- `target` - this is the name of the Xcode target to build.
- `project_directory` - this is the path to the Xcode project on disk.
- `output_directory` - this is where the resulting builds will be output, it is recommended to use Dropbox or another file sharing service.
- `git_repo` - this is the url of the git repository to build from.
- `configurations` - this is a dictionary of the various build configurations where the key is the configuration name, and the value is another dictionary of options.

## Configuration Options

Each build can have it's own configuration options. The `release` key is treated special and will cause a `.xcarchive` file that you can submit to the app store.

- `git_branch` - this is the git branch to checkout from the `git_repo`. If the version number of the app in this branch is different than the last build a build is kicked off.
- `display_name` - this is the name to use as the display name of the built application.
- `identity` - this is common the name of the keychain certificate. This certificate must be present on the machine.
- `mobileprovision` - this is the path to the `.mobileprovision` file to use to code-sign this build. This path can be relative to the `buildly.plist` file.
- `icon_directory` - this is the path to a directory of icons to use for the resulting build. This path can be relative to the `buildly.plist` file.

### Hooks

There are several points in the build process for you to run your own code. Supported script types are: *python*, *bash*, *ruby*.

- `ipa_package_hook` - This it the path to a script that will run when the ipa package is made, but before it has been code signed so you can use this to modify the files in the app in any way. The app bundle is passed to this script as argument `$1`. This path can be relative to the `buildly.plist` file.
- `post_build_hook` - This is the path to a script that will run after the build has completed. This can be used to send out emails, update server assets, or do whatever you like. The app version number is passed to this script as argument `$1`. This path can be relative to the `buildly.plist` file.

### HockeyApp

Configuration options related to HockeyApp are stored in a dictionary with the key`hockeyapp`. When a new build is kicked off Buildly checks the last version for the build in HockeyApp and then gathers up all the commit messages between the two build tags. Any lines in the commit messages that begin with `-` will be included as bulleted items in the release notes.

- `teamToken` - This is the HockeyApp team token. This token must be granted read/write permissions.
- `appIdentifier` - This is the app identifier for the specific build.
- `notify` - This is a bool value, if `YES` HockeyApp will send an email notification that a new build is available. Default is `NO`.
- `status` - This is an enum (represented by a string in the plist), valid values are: `available` or `unavailable`. Default is `unavailable`.
- `mandatory` - This is a bool that defines if the release is mandatory or not. The default is `NO`.
- `tags` - This can be an array or a single tag as a string. If specified only users with the tag will be notified of the new build.
- `additionalNotes` - Any additional notes you want included at the bottom of the release notes. This is an easy way to include information with every build like test account credentials.
- `notesType` - This is an enum (represented by a string in the plist), valid values are: `textile` or `markdown`. The default is `textile`.

### TestFlight

Due to Buildly's modular structure support for TestFlight could be added but is not available at this time. Pull requests welcome :)

# buildly.py

`buildly.py` is the main command line script that contains all the logic for watching the git repository for changes and kicking off the various builds.

# lib/buildly.py

`lib/buildly.py` contains the high-level methods involved with building the app, modifying the bundle, packaging it into an ipa, re-codesigning, uploading to HockeyApp, and creating the `.xcarchive` for `release` builds.

# lib

The rest of the scripts in `lib` should be self explanatory and relate to Xcode, HockeyApp, Git, and other low level tasks.

# mobileprovisionPlist

`mobileprovisionPlist` is command line tool that extracts the plist from a `.mobileprovision`. This is used during the codesigning but is also handy to looking at and debugging `.mobileprovision` files.
