#!/bin/sh
# wrapper script to pull the latest site content and redeploy

cd  $(dirname $0)

# see where in the history we are now
PREV=$(git rev-parse --short HEAD)

git pull --ff-only || exit 1

if git diff --name-only $PREV | grep -qE '^(templates/|app\.py|users\.cfg)' ; then
    echo "Configuration or template change detected"
    disposition=reload-or-restart
fi

if git diff --name-only $PREV | grep -q Pipfile.lock ; then
    echo "Pipfile.lock changed"
    pipenv install || exit 1
    disposition=restart
fi

if [ "$1" != "nokill" ] && [ ! -z "$disposition" ] ; then
    systemctl --user $disposition plaidweb.site.service
fi

echo "Updating the content index..."
pipenv run flask publ reindex

count=0
while [ $count -lt 5 ] && [ ! -S $HOME/.vhosts/plaidweb.site ] ; do
    count=$(($count + 1))
    echo "Waiting for service to restart... ($count)"
    sleep $count
done

#pipenv run pushl -rvvc $HOME/var/pushl http://plaidweb.site/feed https://plaidweb.site/feed
