set -e
node scripts/gen-themes.mjs

# Tailwind can't glob the python3.X directory, so point a fixed path at the installed
# md2html_tailwind4 (its converter emits utility classes that must be compiled).
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
MD2HTML=$("$PY" -c "import md2html_tailwind4, os; print(os.path.dirname(md2html_tailwind4.__file__))")
ln -sfn "$MD2HTML" .tw-md2html
trap 'rm -f .tw-md2html' EXIT

npx @tailwindcss/cli -i styles.css -o whiteneuron/static/base/css/styles.css --minify
