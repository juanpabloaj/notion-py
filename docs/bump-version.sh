#!/usr/bin/env bash


VERSION_FILE="notion/__init__.py"


[[ "$1" != @(major|minor|patch) ]] && {
    echo "./$0 <major|minor|patch>"
    exit 1
}
[[ "master" != "$(git branch | grep '* ' | cut -c3-)" ]] && {
    echo "git says that you are not on master branch"
    echo "please checkout and run this script again :)"
    exit 1
}
git status | grep "not staged for commit" > /dev/null && {
    echo "git says that there are uncommited changes"
    echo "please fix them and run this script again :)"
    exit 1
}

old_tag=$(git tag | tail -1)
old_num=$(echo "$old_tag" | cut -c2-)

major=$(echo "$old_num" | cut -d. -f1)
minor=$(echo "$old_num" | cut -d. -f2)
patch=$(echo "$old_num" | cut -d. -f3)

[[ "$1" == "major" ]] && major=$((major + 1))
[[ "$1" == "minor" ]] && minor=$((minor + 1))
[[ "$1" == "patch" ]] && patch=$((patch + 1))

new_num="$major.$minor.$patch"
new_tag="v$new_num"

echo "bumping  $old_num  to  $new_num"

# replace version and add it to git
sed --in-place "s/$old_num/$new_num/" "$VERSION_FILE"
git add "$VERSION_FILE"

# create commit and tag
git commit -m "'Release: $new_tag'"
git tag "$new_tag"

# push commit and tag
git push origin master
git push origin "$new_tag"

echo
echo "done."
