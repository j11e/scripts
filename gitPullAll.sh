#!/usr/bin/env zsh

################################################################################
#
#   gitPullAll.sh
#
#   Simple utility script to put in your $PATH. It walks all subdirectories of
#   the current directory and tries to "update" the git content by stashing
#   non-committed changes, calling `git fetch` then `git pull`, and popping
#   the stash if something was stashed. If the current branch is not develop,
#   the develop branch is also pulled.
#
#   Using the --merge option will also kinda enforce the gitflow workflow, by
#   merging the develop branch in the current branch, if the current branch
#   is a feature branch (guessed by looking for the word "feature" in the 
#   branch name).
#
################################################################################

CURDIR=$(pwd)

# 
# if MERGEFEATURES = "1", then the branches whose name start with
# "feature" will have develop merged in them
#
MERGEFEATURES="0"
if [ "$#" = "1" ]; then
    if [ "$1" = "--merge" ]; then
        echo "\e[36mWill merge develop into feature branches.\e[0m"
        echo ""
        MERGEFEATURES="1"
    fi
fi

echo "\e[36mStarting at $CURDIR.\e[0m"

for directory in $(find ./ -maxdepth 1 -type d | tail -n +2)
do
    echo -e "\e[36mProcessing \e[33m$directory.\e[0m"
    echo ""

    cd $directory

    curbranch=$(git branch | grep "*" | awk '{print $2}')

    if [ -d ".git" ]; then
        echo -e "\e[32mGit repo found, on branch \e[33m$curbranch \e[0m"
 
        #
        # PROCESS:
        # stash, fetch, pull, then stash pop if the initial stash worked
        #

        hasStashed=$(git stash | awk '{print $1}' | wc -l)
       
        # fetch and pull
        git fetch -p
        git pull --rebase
        
        # pull develop too
        if [ "$curbranch" != "develop" ]; then
            echo -e "\e[36mPulling develop too.\e[0m"
            git checkout develop
            git pull --rebase
            git checkout $curbranch
        fi

        # merge dev in feature branches if option on
        if [ "$MERGEFEATURES" = "1" ]; then
            isFeatureBranch=$(echo "$curbranch" | grep -e "^feature" | wc -c)
            
            if [ "$isFeatureBranch" != "0" ]; then
                echo "\e[36mMerging develop into feature branch.\e[0m"
                git merge develop
            fi
        fi

        # popping stash when initial stash worked
        if [ "$hasStashed" = "2" ]; then
            echo "\e[36mInitial git stash worked; popping stash.\e[0m"
            git stash pop
        fi
    else
        echo -e "\e[31mNo git repo here.\e[0m"
    fi
    
    cd ..
    
    echo ""
done
