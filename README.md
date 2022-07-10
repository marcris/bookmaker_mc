# BookMaker
A Book Authoring Application in Python - inspired by Gitbook-Legacy

BookMaker is a book authoring application in Python.

Introduction
------------
* BookMaker facilitates authoring using MarkDown, with a live preview.
* Handles a complete book with a live tree display of chapters, sections and subsections.
* Exporting to EPUB
* Exporting to PDF (generating suitable HTML and CSS for Prince)

How to install it?
------------
Using poetry (https://python-poetry.org/)

If you don't already have poetry:
```txt
curl -sSL https://install.python-poetry.org | python3 -
```
then
```txt
git clone https://github.com/marcris/bookmaker_mc.git
cd bookmaker_mc
poetry build
pip3 install dist/*.whl
```
If poetry build results in
```txt
  ModuleNotFoundError

  No module named 'virtualenv.activation.xonsh'

  at <frozen importlib._bootstrap>:973 in _find_and_load_unlocked
```
then try
```txt
pip uninstall virtualenv
```
Poetry build <u>should</u> give something like this
```txt
Building bookmaker_mc (0.6.0)
  - Building sdist
  - Built bookmaker_mc-0.6.0.tar.gz
  - Building wheel
  - Built bookmaker_mc-0.6.0-py3-none-any.whl
```


Run using the command 'bm'.

Links
------------
* BookMaker GitHub repository including documentation (in preparation) <https://github.com/marcris/BookMaker_mc>
