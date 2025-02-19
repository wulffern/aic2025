#!/usr/bin/env python3

import re
import os
import click
from sys import platform
import shutil
import urllib.parse
import hashlib

class Image():

    def __init__(self,imgsrc,options):
        self.src = imgsrc
        self.orgsrc = imgsrc
        self.options = options
        self.directory = options["dir"]
        self.skip = False
        self.isUrl = False


        if("/ip/" in self.src and "allowIP" not in self.options):
            self.skip = True

        if(re.search(r"\s*https?://",self.src)):
            self.isUrl = True


        if(not self.skip and ".pdf" in self.src and "latex" not in self.options):
            #- I've changed to svg, hopefully better images
            svg = self.src.replace(".pdf",".svg")
            if(not os.path.exists(os.path.join(self.directory,svg))):
                cmd = f"cd {self.directory}; pdftocairo -svg {self.src} {svg}"
                os.system(cmd)
            self.src = svg

        if(self.isUrl and "downloadImage" in self.options):
#            print(self.src)
            url = self.src
            arr = url.split("?")
            end = arr[0].split(".")[-1]
            self.src = "/tmp/" +  hashlib.sha256(os.path.basename(self.src).encode()).hexdigest() + "." + end
#            print(self.src)
            if(not os.path.exists(self.src)):
                os.system(f"cd /tmp/; wget {url} -O {self.src}")


        self.filesrc = os.path.basename(self.src)
        self.dirsrc  = os.path.dirname(self.src)


    def copy(self):
        if(self.isUrl and not ("downloadImage" in self.options) ):
            return
            
        if(self.skip):
            return

        if("jekyll" in self.options):
            shutil.copyfile(os.path.join(self.options["dir"],self.src), "docs/assets/media/" + self.filesrc)
        elif("latex" in self.options):
            os.makedirs(self.options["latex"] + "media/",exist_ok=True)
            try:
                shutil.copyfile(os.path.join(self.options["dir"],self.src),  self.options["latex"] + "media/" + self.filesrc)
                if("pdf" in self.src in self.src):
                    shutil.copyfile(os.path.join(self.options["dir"],self.src.replace(".pdf",".svg")),  self.options["latex"] + "media/" + self.filesrc.replace(".pdf",".svg") )
                if("svg" in self.src in self.src):
                    shutil.copyfile(os.path.join(self.options["dir"],self.src.replace(".svg",".pdf")),  self.options["latex"] + "media/" + self.filesrc.replace(".svg",".pdf") )
            except Exception as e:
                print(e)
    def __str__(self):

        if(self.skip):
            return f"> image {self.src} removed"

        if("jekyll" in self.options):
            path = self.options["jekyll"] + "assets/media/" + self.filesrc

            return f"![]({path})" + "{: width=\"700\" }\n"
        elif("latex" in self.options):

            if(self.dirsrc == "/tmp"):
                path = "/tmp/" + self.filesrc
            else:
                path = "media/" + self.filesrc
            #print(path)

            return f"<!-- {self.orgsrc} -->\n\n![]({path})\n\n"

        return self.src

class Lecture():
    
    def __init__(self,filename,options):
        self.filename = filename
        self.title = ""
        self.options = options
        self.date = None
        self.images = list()

        self.filters = {
            r"^\s*---\s*$" : "",
            r"\[.column\]" : "",
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "# ",
            r"\*\*Q:\*\*" : "",
            r"^[.table.*]$": "",
            r"#(.*) Thanks!" : ""
        }

        self._read()

    def copyAssets(self):
        with open("images.txt","a") as fo:
            for image in self.images:
                if(not image.skip and not image.isUrl):
                    fo.write(image.orgsrc + "\n")
                    fo.write(image.src +"\n")
                image.copy()


    def _read(self):

        self.buffer = list()
        first = True
        self.output = False
        self.skipslide = False
        self.removeComment = False

        with open(self.filename) as fi:
            for line in fi:

                if(first and "date:" in line):
                    (k,v) = line.split(" ")
                    self.date = v.strip()

                if(first and re.search(r"^\s*$",line)):
                    first = False
                    self.output = True


                line = self._readPan(line)

                if(line):
                    line = self._filterLine(line)
                    line = self._convertImage(line)


                if(line is not None and self.output):
                    self.buffer.append(line)



    def _readPan(self,line):

        #- Check pan tags
        m = re.search(r"<!--pan_([^:]+):(.*)$",line)
        if(m):
            key = m.groups()[0]
            val = m.groups()[1]


            if(key == "title"):
                self.title = val.replace("-->","")

            elif(key == "skip"):
                self.skipslide = True
                self.output = False

            elif(key == "doc"):
                 # Start statemachine
                # 1. Skip this line, it should be <!--pan_doc:
                # 2. Enable removing -->
                # 3. When -->, assume that's the end of the pan_doc, and go back to normal
                self.removeComment = True
            else:
                print(f"Uknown key {key}")

            return None

        #- Go back to normal mode
        if(self.removeComment and re.search(r"-->",line)):
            self.removeComment = False
            return None

        if(self.skipslide and re.search(r"^\s*---\s*$",line)):
            self.output = True
        return line

    def _convertImage(self,line):
        m = re.search(r"\!\[([^\]]*)\]\(([^\)]+)\)",line)

        if(m):
            imgsrc = m.groups()[1]

            if(not "downloadImage" in self.options):
                if(re.search(r"\s*https://",imgsrc)):
                    return f"![]({imgsrc})"

            i = Image(imgsrc,self.options)
            self.images.append(i)
            line = str(i)
        return line


    def _filterLine(self,line):
        for r,s in self.filters.items():
            line = re.sub(r,s,line)
        return line

    def __str__(self):

        ss = ""

        if("jekyll" in self.options):

            furl = "https://github.com/wulffern/aic2025/tree/main/" + self.filename
            slides = ""
            if("lectures" in self.filename ):
                slides = "[Slides](" +  self.options["jekyll"] + self.filename.replace("lectures","assets/slides").replace(".md",".pdf") +")"

            ss += f"""---
layout: post
title: {self.title}
math: true
---

> If you find an error in what I've made, then [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo), fix [{self.filename}]({furl}), [commit](https://git-scm.com/docs/git-commit), [push](https://git-scm.com/docs/git-push) and [create a pull request](https://docs.github.com/en/desktop/contributing-and-collaborating-using-github-desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request). That way, we use the global brain power most efficiently, and avoid multiple humans spending time on discovering the same error.

{slides}


""" + """



* TOC
{:toc }

"""

        for l in self.buffer:
            ss += l
        return ss

class Presentation(Lecture):

    def __init__(self,filename,options):
        self.filename = filename
        self.title = filename.replace(".md","")
        self.options = options

        self.images = list()

        self.filters = {
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "## ",
            r"^[.table.*]$": "",
            r"\!\[[^\]]+\]" : "![]",
            r"^# ":"## ",
            r"\[.column\]" : "",
            #"^---":"#",

        }

        self._read()

    def _read(self):

        self.buffer = list()
        first = True
        self.output = False
        self.skipslide = False
        self.removeComment = False

        with open(self.filename) as fi:
            for line in fi:

                if(first and re.search(r"^\s*$",line)):
                    first = False
                    self.output = True

                key = ""
                val = ""
                m = re.search(r"<!--pan_([^:]+):(.*)$",line)
                if(m):
                    key = m.groups()[0]
                    val = m.groups()[1]


                if(key == "title"):
                    self.title = val.replace("-->","")

                if(re.search(r"^<!--",line)):
                    self.output = False

                line = self._filterLine(line)
                line = self._convertImage(line)

                if(line is not None and self.output):
                    self.buffer.append(line)

                if(re.search(r"-->",line)):
                    self.output = True

    def __str__(self):

        ss = ""

        ss += f"""---
title: {self.title}
output:
  slidy_presentation:
    footer: "Copyright (c) 2025, Carsten Wulff"
    fig_width: 800
---

""" + """




"""
        for l in self.buffer:
            ss += l
        return ss

class Latex(Lecture):

    def __init__(self,filename,options):
        self.filename = filename
        self.title = filename.replace(".md","")
        self.options = options

        self.images = list()

        self.filters = {
             r"^\s*---\s*$" : "",
            r"\[.column\]" : "",
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "# ",
            r"\#\#\s*\[\s*fit\s*\]" : "## ",
            #"^## \*\*Q:\*\*.*$" : "",
            r"^[.table.*]$": "",
            r"^\* TOC":"",
            r"^{:toc }":"",
            r"\*\*Q:\*\*" : "",
            r"#(.*) Thanks!" : ""
            #"^---":"#",
        }

        self._read()



    def __str__(self):

        ss = ""

        ss += f"""

""" + """




"""
        for l in self.buffer:
            ss += l
        return ss


    

@click.group()
def cli():
    """
    Convert a lecture to something
    """
    pass

@cli.command()
@click.argument("filename")
@click.option("--root",default="/aic2025/",help="Root of jekyll site")
@click.option("--date",default=None,help="Date to use")
def post(filename,root,date):
    options = dict()
    options["jekyll"] = root
    options["dir"] = os.path.dirname(filename)

    if(not os.path.exists("docs/assets/media/")):
        os.mkdir("docs/assets/media/")

    if(not os.path.exists("docs/_posts")):
        os.mkdir("docs/_posts")

    #- Post
    l = Lecture(filename,options=options)

    if(date is None and l.date is not None):
        date = l.date
    else:
        raise Exception(f"I need a date, either in the frontmatter, or the option for {filename}")

    l.copyAssets()
    fname = "docs/_posts/" + date +"-"+ l.title.strip().replace(" ","-") + ".markdown"

    with open(fname,"w") as fo:
        fo.write(str(l))



    


@cli.command()
@click.argument("filename")
@click.option("--root",default="pdf/",help="output roote")
def latex(filename,root):
    options = dict()
    options["latex"] = root
    options["downloadImage"] = True
    options["allowIP"] = True
    options["dir"] = os.path.dirname(filename)
    p = Latex(filename,options)
    p.copyAssets()


    fname = root + os.path.sep + p.title.strip().replace(" ","_").lower() + ".md"
    with open(fname,"w") as fo:
        fo.write(str(p))

    with open("pdf/chapters.tex","a") as fo:
        fo.write(r"\setchapterstyle{kao}" + "\n")
        fo.write(r"\setchapterpreamble[u]{\margintoc}"+ "\n")
        title = p.title.strip()
        title = re.sub(r"Lecture\s+[\d|X]*\s+-\s+","",title)
        fo.write(r"\chapter{"+title+"}"+ "\n")
        fo.write(r"\input{"+p.title.strip().replace(" ","_").lower()+"_fiximg.tex}"+ "\n\n")

    flatex = fname.replace(".md",".latex")
    cmd = f"pandoc --citeproc --bibliography=pdf/aic.bib --csl=pdf/ieee-with-url.csl  -o {flatex} {fname}  "
    os.system(cmd)
    cmd = f"pandoc -s --citeproc --bibliography=pdf/aic.bib --csl=pdf/ieee-with-url.csl  -o {flatex}_standalone.tex {fname}  "
    os.system(cmd)




if __name__ == "__main__":
    cli()
