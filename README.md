# HOT Template Generator
## heatgen
Generates a HOT template from a YAML specification. There is a sample specification in the **samples** directory.

```
usage: heatgen [-h] input

Generate a HOT template.

positional arguments:
  input       Input YAML specification
```

# OCUDR automation scripts
## stackcreate
Using the Heat API, creates a stack from a generated HOT template.

```
usage: stackcreate [-h] name imagename yaml keyname

Creates a stack from a HOT template

positional arguments:
  name        Name of the stack to create.
  imagename   Name of the image to use for the stack
  yaml        HOT template for the stack.
  keyname     Name of the keypair to use.
```

## stackconfigure
Pulls metadata from Heat, and uses the AppWorks MMI to configure the system.

```
usage: stackconfigure [-h] stackname keyfile

Configures a stack created using stackcreate.py

positional arguments:
  stackname   Name of the stack to configure.
  keyfile     Path to SSH key to use for authentication.
```
