# These xml files are for BookMaker to use in EPUB generation

container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>
"""

content_opf = """<?xml version="1.0" encoding="utf-8" ?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf"
                       unique-identifier="BookId">

<!-- Metadata section -->
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <!--Required Metadata-->
    <dc:title>{title}</dc:title>
    <dc:language>en-gb</dc:language>
    <dc:identifier id="BookId">urn:isbn:{ISBN}</dc:identifier>
    <!--Make sure to use the same id in the toc.ncx file -->
    <dc:creator id="aut">{author}</dc:creator>
    <dc:rights>© 2020 by Chris C. Brown and Marcris Software.</dc:rights>
    <dc:publisher>{author}</dc:publisher>
    <meta name="cover" content="cover-image" /> <!--Required for KindleGen-->
    <meta property="dcterms:modified">{date}</meta>
  </metadata>

  <manifest>
    <item id="cover"       href="cover.xhtml"    media-type="application/xhtml+xml"/>
    <item id="cover-image" href="cover.png" media-type="image/png"/>
      <!-- The media-type attributes in the manifest are just mimetypes. Some other examples:
      gifs: "image/gif"
      jpegs: "image/jpeg"
      PNG: "image/png"
      otf: "font/opentype"
      ttf: "font/truetype"
      -->

    <!-- <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" /> -->
    <item id="github-markdown_css" href="_css/github-markdown.css"  media-type="text/css" />
    <item id="github-pygments_css" href="_css/github-pygments.css"  media-type="text/css" />

    <item id="nav" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav" />
    
    <!-- The correct mime-type for ncx files is 'application/x-dtbncx+xml' -->
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
    <!-- toc.ncx mandatory for EPUB 2 documents; not needed in EPUB 3 except for compatibility -->

    <!-- <item href="coverpage.html" id="htmlcoverpage" media-type="application/xhtml+xml" /> -->
    <!-- Do not add a coverpage.html file for the Kindle -->

    <!-- Insert links to HTML content files here -->
"""

toc_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
<title>toc.xhtml</title>
</head>

<body>

    <nav id="toc" epub:type="toc">
        <h1 class="frontmatter">Table of Contents</h1>
        <ol class="contents">
"""
toc_xhtml_end = """
        </ol>
    </nav>

</body>
</html>"""

toc_ncx = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
    <!-- Metadata Section -->
    <head>
        <meta name="dtb:uid" content="urn:isbn:{ISBN}"/> <!-- Must be exactly the same as dc:identifier in the content.opf file -->
        <meta name="dtb:depth" content="2"/> <!-- Set for 2 if you want a sub-level. It can go up to 4 -->
        <meta name="dtb:totalPageCount" content="0"/> <!-- Do Not change -->
        <meta name="dtb:maxPageNumber" content="0"/> <!-- Do Not change -->
    </head>
    <!-- Title and Author Section -->
    <docTitle>
        <text>Programming Python with GTK + and SQLite</text>
    </docTitle>

    <!-- Navigation Map Section -->
    <navMap>
"""
toc_ncx_end = """
    </navMap>
</ncx>"""

cover_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Your title here</title>
  </head>
  <body>
    <img src="cover.png" alt="Cover Image" />
  </body>
</html>"""
