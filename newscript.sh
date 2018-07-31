#!/usr/bin/env zsh

################################################################################
# newscript.sh
#
# Creates a new script executable file by copying a template, and opens it in
# a text editor (default: SublimeText). 
# Which template is used is guessed from the extension used in scriptname.ext 
# (default: shell).
# Within the template, "{name}" is replaced with the actual script name.
#
# usage: newscript.sh scriptname.ext [editor_command]
################################################################################

# check parameter count
if [[ "$#" -lt 1 || "$#" -gt 2 ]];
then
	echo "Usage: newscript.sh scriptname.ext [editor_command]"
fi

# default values
EDITOR_COMMAND='subl'
TEMPLATE_NAME='shell_template'
TEMPLATE_DIR=$(dirname $0:A)
SCRIPT_NAME="$1"

# find out template name from parameters (if extension indicated)
SCRIPTNAME_EXTENSION=$(echo "$1" | cut -d'.' -f2)
if [[ "$SCRIPTNAME_EXTENSION" == "py" ]];
then
	TEMPLATE_NAME='python_template'
fi

# find out which editor to use from parameters
if [[ $2 != "" ]];
then
	EDITOR_COMMAND="$2"
fi

# copy template, replace {name} with the name, make it exectuable, and edit it
cp "$TEMPLATE_DIR/$TEMPLATE_NAME" "./$SCRIPT_NAME"

sed -i "s/{name}/$SCRIPT_NAME/g" "./$SCRIPT_NAME"

chmod +x "./$SCRIPT_NAME"

$EDITOR_COMMAND $SCRIPT_NAME
