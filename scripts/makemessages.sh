cd whiteneuron
mkdir -p locale
django-admin makemessages -l vi --ignore "node_modules/*"
cd ..