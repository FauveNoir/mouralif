#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Mouralif: mainfile

import sys
import itertools
import os
import re
import datetime
import pypdftk
import glob
import readline
import gi
import subprocess
import platform
import threading
import Xlib
import pint
import tempfile
import unicodedata
import gettext
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GdkPixbuf

from optparse import OptionParser
from PyPDF2 import PdfFileWriter, PdfFileReader
from latex import build_pdf
from colorthief import ColorThief
from pdf2image import convert_from_path



progname = "Mouralif"
version = "0.1"
usage = "usage: %prog "
parser = OptionParser(usage=usage, version="%prog 0.1")

parser.add_option("-f",              help="The file to process",
                  default=0, action="store", dest="fileToProcess")
parser.add_option("-w",              help="Spin’s width",
                  default=0, action="store", dest="spinWidth")
parser.add_option("-l",              help="The left spin inscription",
                  default=0, action="store", dest="leftInscription")
parser.add_option("-m",              help="The middle spin inscription",
                  default=0, action="store", dest="centerInscription")
parser.add_option("-r",              help="The center right inscription",
                  default=0, action="store", dest="rightInscription")
parser.add_option("-c",              help="The the background spin color",
                  default=0, action="store", dest="spin")

(options, args) = parser.parse_args()

pdfFile=options.fileToProcess

def getPdfMetadata(pdf):
    # -> Objet PDF
    # <- pdf_info
    # Récupère les métadonnées du pdf, comme le nom de l’auteur, du pdf, et de la date
    # en vue de les proposer comme inscriptions sur la tranche.
    pdf_toread = PdfFileReader(open(pdf, "rb"))
    pdf_info = pdf_toread.getDocumentInfo()
    return pdf_info

def organizeDefaultSpinInscription(metadata):
    # -> pdf_info
    # <-  Liste [AUteur, Titre, date]
    # Dispose les données du PDF précédement prélevées dans une liste
    # En attribuant les positions par défaut selon chaque donnée
    spinInscriptions=["", "", ""]
    if "/Author" in metadata:
        spinInscriptions[0]=metadata["/Author"]
    if "/Title" in metadata:
        spinInscriptions[1]=metadata["/Title"]
    if "/CreationDate" in metadata:
        spinInscriptions[2]=metadata["/CreationDate"]

    return spinInscriptions

def getInscriptions(pdf):
    # -> objet PDF
    # <- Liste organisée de métadonées [Auteur, Titre, date]
    # Récupère ET organise les métadonées d’un fichier pdf.
    metadata=getPdfMetadata(pdf)
    inscriptions=organizeDefaultSpinInscription(metadata)

    return inscriptions




def isolateNthPage(Nth,pdf,label):
    # -> Nombre de pages, objet pdf, sufixe
    # Isole la dernière page du pdf en vue de la concatener avec la première page dans la couverture finale.
    inputpdf = PdfFileReader(open(pdf, "rb"))
    output = PdfFileWriter()
    output.addPage(inputpdf.getPage(Nth))
    
    newname = pdf[:7] + "-"  + label + ".pdf"
    
    outputStream = open(newname, "wb")
    output.write(outputStream)
    outputStream.close()

def getPageDim(pdf):
    # -> objet pdf
    # <- hauteur de page, largeur de page
    pdfFile = PdfFileReader(open(pdf, 'rb'))
    height= pdfFile.getPage(0).mediaBox[3]
    width= pdfFile.getPage(0).mediaBox[2]
    return height,width

def isolateFirstPage(pdf):
    # Construction de la couverture
    isolateNthPage(0, pdf, "first")

def isolateLastPage(pdf):
    # -> objet pdf
    # Isole la dernière page du pdf en entrée en vue de la concaténation dans la couverture finale.
    lastPageNumber=getLastPage(pdf)-1
    isolateNthPage(lastPageNumber, pdf, "last")

def convertFirstPageToimage(path):
    # -> objet pdf
    # Converti la première page en image en vue d’en extraire la couleur dominante.

    global FirstPageFileName

    firstPagePath=FirstPageFileName.name
    outputName=makeTempExampleName(path)
    print("Alert " + outputName)
    page = convert_from_path(firstPagePath, 0)
    page[0].save(outputName, 'JPEG')

def ratioiseRGBcolorItem(item):
    # Transforme un item du triblet RGB en nombre à deux chiffre héxadécimal.
    print("received item is: " + str(item))
    return (item/255*65535)

def makeColorObject(colorTuple):
    # Transforme la couleure RGB récupérée sur la couverture du PDF en code héxadécimal
    red=ratioiseRGBcolorItem(colorTuple[0])
    green=ratioiseRGBcolorItem(colorTuple[1])
    blue=ratioiseRGBcolorItem(colorTuple[2])
    colorObject=Gdk.Color(red, green, blue)

    return colorObject

def defineMainColor(path):
    # Définit la couleur principale par défat de la couverture.
    viewWaitingMessage("Detection de la couleur dominante")
    convertFirstPageToimage(path)
    color_thief = ColorThief(makeTempExampleName(path))
    dominant_color = color_thief.get_color(quality=1)
    print("dominant color is")
    print(dominant_color)
    gtkDominantColor=makeColorObject(dominant_color)

    return gtkDominantColor

def formateColor(color):
    # Formate les items de couleur de sorte à former un item RGB
    formatedcolor=str(color[0]) + "," + str(color[1]) + "," + str(color[2])
    return formatedcolor

def normalizeHex(hexnum):
    # Cas particulier dans le formatage de la couleure héxadécimale :
    # Si  le bi-chiffre héxadécimal est composé d’un seul chiffre, ajoute un zéro non significatif au début.
    if len(hexnum) == 1:
        return "0" + hexnum
    return hexnum

def gdk_to_hex(gdk_color):
    # Transforme les couleurs GTK en couleure HTML
    colors = gdk_color.to_floats()
    print(colors)
    htmlcode = ""
    for color in colors:
        hexDigit=normalizeHex(hex(int(color*255)).lstrip("0x"))
        print(hexDigit)
        htmlcode=htmlcode +str(hexDigit)
    print(htmlcode)
    return htmlcode

def minimizeRGBColors(bigColor):
    # Transforme un item du triblet RGB en nombre à deux chiffre héxadécimal.
    smallColor=bigColor/65535*255
    return smallColor

def gdk_to_rgb(gdk_color):
    # Transforme les couleurs GTK en couleure HTML
    red = minimizeRGBColors(gdk_color.red)
    green = minimizeRGBColors(gdk_color.green)
    blue = minimizeRGBColors(gdk_color.blue)

    rgbColor={
        "red"   : red,
        "green" : green,
        "blue"  : blue,
    }
    return rgbColor

def makeFirstPage(configuration):
    # Prépare le code LaTeX d’inclusion de la première page
    latexCode="\includegraphics{\\firstpagename}"
    return latexCode

def makeLastPage(configuration):
    latexCode=whatToDoForLastPage(configuration)
    return latexCode

def makeRightSide(configuration):
    if configuration["orientation"]:
        return makeFirstPage(configuration)
    return makeLastPage(configuration)

def makeLeftSide(configuration):
    if not configuration["orientation"]:
        return makeFirstPage(configuration)
    return makeLastPage(configuration)

def pointToMilimeterConvertion(inputPointvalue):
    #Conversion des points typographiques en milimètres
    # l’environement minipage de LaTeX gère mal les points
    print(type(inputPointvalue))
    milimetervalue=float(inputPointvalue)*0.352778
    print(milimetervalue)
    return str(milimetervalue)


def makeTheTeXfile(configuration):
    # Prépare le code source LaTeX en vue de la concaténation
    global FirstPageFileName
    firstPageName=FirstPageFileName.name


    color=gdk_to_hex(configuration["color"])
    print("First page name is: " + firstPageName)
    TeXfile="""
    \documentclass{standalone}
    \\usepackage[utf8]{inputenc}
    \\usepackage[T1]{fontenc}
    \\usepackage{pdfpages}
    \\usepackage{graphicx}
    \\usepackage{xcolor}
    \\usepackage[space]{grffile}
    \definecolor{spincolor}{HTML}{""" + color + """}
    
    \def\spinwidth{""" + str(configuration["spinWidth"]) + configuration["unit"] + """}
    \def\spinheight{""" + pointToMilimeterConvertion(str(configuration["pdfHeight"])) + """mm}
    \def\spinleft{""" + configuration["left"] + """}
    \def\spincenter{""" + configuration["center"] + """}
    \def\spinright{""" + configuration["right"] + """}
    \def\\firstpagename{""" + firstPageName + """}
    \definecolor{spinForeground}{HTML}{""" + configuration["forgroundColor"] + """}
    
    \\begin{document}%
    """ + makeLeftSide(configuration)  + """%
    \\rotatebox[origin=bl]{90}{%
    \setlength{\\fboxsep}{0pt}%
    \setlength{\\fboxrule}{0pt}%
    \\noindent\\fcolorbox{spincolor}{spincolor}{%
    \\noindent\\begin{minipage}[b][\spinwidth][c]{\spinheight}
    \color{spinForeground}
      \hspace{0.5cm}\\textbf{\spinleft}\hfill\spincenter\hfill\spinright\hspace{0.5cm}
    
      \\vfill
    \end{minipage}}}%
    """ + makeRightSide(configuration)  + """
    \end{document}
    """
    return TeXfile

def makeUserQuestion(prompt, prefill=''):
    # Prépare les placeholder par défaut de chaque champs des étiquettes.
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt + ": ")  # or raw_input in Python 2
    finally:
        readline.set_startup_hook()


def setInscriptions(pdf):
    # Prépare les placeholder par défaut des champs des étiquettes.
    choosenInscriptions=["", "", ""]
    defaultInscriptions=getInscriptions(pdf)
    choosenInscriptions[0]=makeUserQuestion("Gauche", defaultInscriptions[0])
    choosenInscriptions[1]=makeUserQuestion("Centre", defaultInscriptions[1])
    choosenInscriptions[2]=makeUserQuestion("Droite", defaultInscriptions[2])

    return choosenInscriptions

def setColor(pdf):
    # Déffinir la couleur selectionnée par défaut dans le champs de couleur
    defaultColor=formateColor(defineMainColor())
    choosenColor=makeUserQuestion("Color", defaultColor)

    return choosenColor

def setWidth():
    # Positionne l’épaisseur par défaut de la tranche.
    defaultWidth="1cm"
    choosenWidth=makeUserQuestion("Épaisseur de tranche", defaultWidth)

    return choosenWidth

def makeDefaultOptions(pdf):
    # Déffinit les configurations absolues par défaut
    configuration = {
        "color"  : "FFFFF",
        "left"   : "",
        "center" : "",
        "right"  : "",
        "width"  : "",
    }

def findConfigurations(pdf):
    # Définit les configurations détectées par défaut
    configuration = {
        "color"  : "FFFFF",
        "left"   : "",
        "center" : "",
        "right"  : "",
        "width"  : "",
        "pageNumber" : getLastPage(pdf)
    }
    configuration["left"], configuration["center"], configuration["right"] =setInscriptions(pdf)
    configuration["color"]=setColor(pdf)
    configuration["width"]=setWidth()

    return configuration


def buildLatex(pdf):
    # Lance la compilation du projet LaTeX

    global FinalFileName
    pdfHeight,pdfWidth= getPageDim(pdf)

    configuration=findConfigurations(pdf)
    print(configuration)

    TeXfile=makeTheTeXfile(pdfHeight,pdfWidth,configuration)
    outputpdf = build_pdf(TeXfile)
    outputpdf.save_to(FinalFileName)

def texCodeForLastPageWhenEven(configuration):
    # Portion de code du code-source LaTeX concernant le cas où le nombre de pages est paire
    global LastPageFileName
    lastPagePath=LastPageFileName.name
    texCode="\includegraphics{" + lastPagePath + "}%"
    return texCode

def texCodeForLastPageWhenOdd(width):
    # Portion de code du code-source LaTeX concernant le cas où le nombre de pages est impaire
    texCode="""%
    \setlength{\\fboxsep}{0.385pt}%
    \setlength{\\fboxrule}{0.385pt}%
    \\noindent\\fcolorbox{spincolor}{spincolor}{%
    \\begin{minipage}[b][\spinheight][c]{""" + str(width) + """pt}
    ~
    \end{minipage}}%
    """
    return texCode


def whatToDoForLastPage(configuration):
    # Déffinition de la portion du code TeX selon que la dernière page soit paire ou impaire
    pageNumber=configuration["pageNumber"]

    if pageNumber % 2 == 0:
        return texCodeForLastPageWhenEven(configuration)
    else:
        return texCodeForLastPageWhenOdd(configuration["pdfWidth"])

def makeFirstPageName(pdfPath):
    # Définition du nom du fichier temporaire pour la première page
    newname = os.path.splitext(pdfPath)[0] + "-"  + "first" + ".pdf"
    return newname

def makeLastPageName(pdfPath):
    # Définition du nom du fichier temporaire pour la dernière page
    newname = os.path.splitext(pdfPath)[0] + "-"  + "last" + ".pdf"
    return newname

def makeTempExampleName(pdfPath):
    newname = os.path.splitext(pdfPath)[0] + "-"  + "example" + ".jpg"
    return newname


def makeTheFinalCover(pdf):
    # Construction de la couverture
    isolateFirstPage(pdfFile)
    isolateLastPage(pdfFile)
    buildLatex(pdf)

def isolateFirstPage2(pdf_toread,filename):
    global FirstPageFileName
    outputName = FirstPageFileName.name
    print("Firstpage name: " + outputName)
    isolateNthPage2(0, pdf_toread, filename, outputName)

def isolateLastPage2(pdf_toread,filename):
    global LastPageFileName
    outputName = LastPageFileName.name
    lastPageNumber=getLastPage(filename)-1
    print("last page is: " + str(lastPageNumber))
    isolateNthPage2(lastPageNumber, pdf_toread, filename, outputName)

def isolateNthPage2(Nth, inputpdf, filename, outputName):
    output = PdfFileWriter()
    output.addPage(inputpdf.getPage(Nth))

    outputStream = open(outputName, "wb")
    output.write(outputStream)
    outputStream.close()

def isolatePages(pdf_toread,filename):
    isolateFirstPage2(pdf_toread,filename)
    isolateLastPage2(pdf_toread,filename)

def getFieldFromMetadata(field, metadata):
    # Constructeur pour les fonctions de récupération de chaque métadonée
    formatedFieldName="/" + field
    if formatedFieldName in metadata:
        return metadata["/" + field]
    return ""

def getPdfAuthor(metadata):
    # Fonction de récupération du nom de l’auteur
    viewWaitingMessage("Extraction des métadonées")
    author = getFieldFromMetadata("Author", metadata)
    return author

def getPdfTitle(metadata):
    # Fonction de récupération du nom du titre de l’ouvrage
    title = getFieldFromMetadata("Title", metadata)
    return title

def sanitizeFoundedDate(foundedDate):
    # Fonction d’assainissement de la date de publication
    exp = "^D:(?P<year>[0-9][0-9][0-9][0-9]).*$"
    annalysedDate=re.match(exp, foundedDate)
    try:
        year=annalysedDate.group("year")
    except:
        year=""

    return year

def getPdfDate(metadata):
    # Fonction de récupération du nom de la date de publication de l’ouvrage
    foundedDate = getFieldFromMetadata("CreationDate", metadata)
    title = sanitizeFoundedDate(foundedDate)
    return title

def getLastPage(pdf):
    # -> objet PDF
    # <- int nombre de page
    # Renvoit le numéro de la dernière page
    theLastPageNumber=pypdftk.get_num_pages(pdf_path=pdf)
    return theLastPageNumber

def getPdfHeight(pdf_toread):
    # Récupération de la hauteur de page du pdf
    height=pdf_toread.getPage(0).mediaBox[3]
    return height

def getPdfWidth(pdf_toread):
    # Récupération de la largeur de page du pdf
    width=pdf_toread.getPage(0).mediaBox[2]
    return width

def getRGBsum(red, green, blue):
    RGBsum = red + green + blue
    return RGBsum

def setContrastedColor(RGBsum):
    middleColor=383
    if RGBsum >= middleColor:
        return "000000"
    return "ffffff"

def setForegroundColor(backgroundColor):
    backgroundColor=gdk_to_rgb(backgroundColor)
    RGBsum = getRGBsum(backgroundColor["red"], backgroundColor["green"], backgroundColor["blue"])
    contrastedColor=setContrastedColor(RGBsum)

    return contrastedColor

def getPdfInfo(pdf,pdf_toread):
    # Récupération des informations du PDF pertinantes pour la suite.
    metadata=getPdfMetadata(pdf)
    print(metadata)
    pdfData = {
        "color"      : defineMainColor(pdf),
        "author"     : getPdfAuthor(metadata),
        "title"      : getPdfTitle(metadata),
        "year"       : getPdfDate(metadata),
        "pageNumber" : getLastPage(pdf),
        "pdfWidth"   : getPdfWidth(pdf_toread),
        "pdfHeight"  : getPdfHeight(pdf_toread),
    }

    return pdfData

# Déffinition de la liste des unitées possibles dans lesquelles déffinir l’épaisseur de tranche
listOfUnits = ["mm", "cm", "pt", "px", "in"]

# Les différents types MIME permettant de matcher les pdf
supportedFilesType=[
"application/pdf",
"application/x-pdf",
"application/x-bzpdf",
"application/x-gzpdf",
]

validFileChooser=Gtk.FileChooserDialog("Veuillez choisir un fichier", None,
    Gtk.FileChooserAction.OPEN,
    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
    Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
filter_text = Gtk.FileFilter()
filter_text.set_name("Documents")

for fileType in supportedFilesType:
    filter_text.add_mime_type(fileType)

validFileChooser.add_filter(filter_text)


class GridWindow(Gtk.Window):
    # Construction de l’objet fenêtre


    def on_abtdlg(self, widget):
        about = Gtk.AboutDialog()
        about.set_program_name("Mouralif")
        about.set_version("0.1")
        about.set_authors(["Fauve alias Idriss al Idrissi"])
        about.set_copyright("CC-by-sa Fauve")
        about.set_comments("Utilitaire de génération decouverture complette de livre")
        about.set_website("http://taniere.info")
        logo = GdkPixbuf.Pixbuf.new_from_file("logo-mouralif.png")
        about.set_logo(logo)
        about.run()
        about.destroy()

    def __init__(self):
        global progname
        Gtk.Window.__init__(self, decorated=True, title=progname)
        self.set_icon_from_file('icon.png')

        self.set_border_width(10)

        grid = Gtk.Grid()
        grid.set_row_spacing(3)
        self.add(grid)


        aboutButton = Gtk.Button()
        aboutButton.set_relief(Gtk.ReliefStyle.NONE)
        aboutButton.connect("clicked", self.on_abtdlg)
        img = Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.MENU)
        aboutButton.set_image(img)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = progname
        hb.pack_start(aboutButton)
        self.set_titlebar(hb)




        spinWidth=Gtk.Adjustment(value=10, lower=0, upper=5000, step_increment=1)


        unit_store = Gtk.ListStore(str)
        unit_store = Gtk.ListStore(str)
        units = listOfUnits
        for unit in units:
            unit_store.append([unit])


        donateImage = Gtk.Image()
        donateImage.set_from_file("./please-donate.png")

        self.fileChooser = Gtk.FileChooserButton.new_with_dialog(validFileChooser)
        self.fileChooser.connect("selection-changed", on_file_selected_no_lag)
        labelSpinWidth = Gtk.AccelLabel(label="Épaisseur de tranche")
        self.inputWidthSelector = Gtk.SpinButton.new(adjustment=spinWidth,climb_rate=1, digits=2 )

        self.inputUnitStore = Gtk.ComboBox.new_with_model(unit_store)
        self.inputUnitStore.set_active(0)
        renderer_text = Gtk.CellRendererText()
        self.inputUnitStore.pack_start(renderer_text, True)
        self.inputUnitStore.add_attribute(renderer_text, "text", 0)

        spinSizeStack=Gtk.StackSwitcher(spacing=0)
        spinSizeStack.pack_start(self.inputWidthSelector, True, True, 0)
        spinSizeStack.pack_start(self.inputUnitStore, True, True, 0)

        self.labelLeftInscription = Gtk.AccelLabel(label="Gauche")
        self.entryLeftInscription = Gtk.Entry(placeholder_text="John Doe")
        labelCenterInscription = Gtk.AccelLabel(label="Centre")
        self.entryCenterInscription = Gtk.Entry(placeholder_text="The Best Book")
        labelRightInscription = Gtk.AccelLabel(label="Droite")
        self.entryRightInscription = Gtk.Entry(placeholder_text="2019")
        labelSpinColor = Gtk.AccelLabel(label="Couleur de tranche")
        self.buttonSelectSpinColor = Gtk.ColorButton.new()
        self.buttonCreate = Gtk.Button(label="Créer la couverture")
        self.buttonCreate.set_sensitive(False)
        self.buttonCreate.connect("clicked", createTheCover)
        self.spiner = Gtk.Spinner()
        self.LabelState =  Gtk.Label(label="")
        buttonDonate = Gtk.LinkButton(uri="https://paypal.me/ihidev", image=donateImage)
        #buttonDonate2 = Gtk.LinkButton(uri="https://paypal.me/ihidev", label="Ce logiciel est gratuit mais vous pouvez faire un don et ça serait gentil :)")
        backgroundDonateColor = Gdk.color_parse('#234fdb')
        buttonDonate.modify_bg(Gtk.StateType.NORMAL, backgroundDonateColor)
        buttonDonate.set_always_show_image(True)

        #buttonDonate2.get_child().set_use_markup(True)
        #buttonDonate2.get_child().set_line_wrap(True)
        #buttonDonate2.set_name("donatebutton")

        self.buttonSelectSide=Gtk.Switch()
        self.buttonSelectSide.set_active(True)
        self.buttonSelectSide.props.halign = Gtk.Align.START
        textOrientation=Gtk.AccelLabel(label="Gauche à droite")
        labelOrientation=Gtk.AccelLabel(label="Gauche à droite")
        labelLastPageInclusion=Gtk.AccelLabel(label="Inclure la dernière page")
        self.takeTheInputedLastPage=Gtk.CheckButton()

        grid.attach(self.fileChooser, 0, 0, 3, 1)
        grid.attach(labelSpinWidth, 0, 1, 1, 1)
        grid.attach_next_to(spinSizeStack, labelSpinWidth, Gtk.PositionType.RIGHT, 2, 1)
        grid.attach(self.labelLeftInscription, 0, 3, 1, 1)
        grid.attach_next_to(self.entryLeftInscription, self.labelLeftInscription, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach(labelCenterInscription, 1, 3, 1, 1)
        grid.attach_next_to(self.entryCenterInscription, labelCenterInscription, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach(labelRightInscription, 2, 3, 1, 1)
        grid.attach_next_to(self.entryRightInscription, labelRightInscription, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach(labelSpinColor, 0, 5, 1, 1)
        grid.attach_next_to(self.buttonSelectSpinColor, labelSpinColor, Gtk.PositionType.RIGHT, 1, 1)

        grid.attach_next_to(textOrientation, labelSpinColor, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach_next_to(self.buttonSelectSide,textOrientation , Gtk.PositionType.RIGHT, 2, 1)
        grid.attach_next_to(labelLastPageInclusion,textOrientation , Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach_next_to(self.takeTheInputedLastPage, labelLastPageInclusion, Gtk.PositionType.RIGHT, 2, 1)

        grid.attach_next_to(self.buttonCreate, labelLastPageInclusion, Gtk.PositionType.BOTTOM, 3, 1)

        grid.attach_next_to(self.spiner,self.buttonCreate , Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach_next_to(self.LabelState, self.spiner , Gtk.PositionType.RIGHT, 2, 1)
        grid.attach_next_to(buttonDonate,self.spiner, Gtk.PositionType.BOTTOM, 3, 2)
        #grid.attach_next_to(buttonDonate2, buttonDonate, Gtk.PositionType.BOTTOM, 3, 2)

screen = Gdk.Screen.get_default()
#styleContext = Gtk.StyleContext()

css = b'#donatebutton { min-height: 100px ; background-image: linear-gradient(to bottom right, #0e9afc, #0352fc); color: #f7f7f7; } #donatebutton * { color: white; text-decoration: none; font-size: 15px; }  '
css_provider = Gtk.CssProvider()
css_provider.load_from_data(css)
context = Gtk.StyleContext()
context.add_provider_for_screen(screen, css_provider,
                                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def beginSpiner():
    win.spiner.start()

def stopSpiner():
    print("enter stopSpiner()")
    viewWaitingMessage("")
    win.spiner.stop()

def viewWaitingMessage(message):
    beginSpiner()
    win.LabelState.set_label(message)

def finalMessage(message):
    print("enter finalMessage()")
    stopSpiner()
    win.LabelState.set_label(message)

info = {}
def pdfTreatment(filename):
    # Prétraitemenet du pdf avec :
    # 1) Récupération des métadonnées ;
    # 2) Extraction des pages pertinentes
    global info
    global ProjectLabel

    # 1)
    viewWaitingMessage("Ouverture du fichier PDF")
    print("Alert: Opening pdf file")
    pdf_toread = PdfFileReader(open(filename, "rb"))
    # 2)
    viewWaitingMessage("Extraction des première et dernière page")
    isolatePages(pdf_toread,filename)
    print("Alert: getting informations")
    viewWaitingMessage("Récupération des métadonées")
    info=getPdfInfo(filename,pdf_toread)
    setProjectLabel(info, filename)
    defineFinalOutputFile()
    print("Alert: cuting pages")
    viewWaitingMessage("Extraction des pages")
    print(info)

    return info

def openPdfFile(filepath):
    # Commande d’ouverture du fichier PDF d’entrée qui s’adapte en fonction de l’OS selectionné
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(filepath)
    else:                                   # linux variants
#        subprocess.call(('xdg-open', filepath))
        subprocess.Popen(["xdg-open", filepath])

def on_file_selected_no_lag(widget):
    # Porcéssus à enclencher à la suite de clique sur le bouton
    # sans freeze.
    t = threading.Thread(name='Importing PDF', target=on_file_selected)
    t.start()

    pass

def setLeftEntry(info):
    # Déffinit Le label à utiliser en bas de la tranche d’après les metadonnées du pdf
    if win.entryLeftInscription.get_text() == "":
        win.entryLeftInscription.set_text(info["author"])

def setCenterEntry(info):
    # Déffinit Le label à utiliser au centre de la tranche d’après les metadonnées du pdf
    if win.entryCenterInscription.get_text() == "":
        win.entryCenterInscription.set_text(info["title"])

def setRightEntry(info):
    # Déffinit Le label à utiliser en haut de la tranche d’après les metadonnées du pdf
    if win.entryRightInscription.get_text() == "":
        win.entryRightInscription.set_text(info["year"])


ProjectLabel = None
FirstPageFileName = None
LastPageFileName = None
FinalFileName = None

def prepareTemporaryFile(label):
    temporaryFile=tempfile.NamedTemporaryFile(delete=False, mode='w+b', prefix=progname+"-", suffix="-"+label+".pdf")
    return temporaryFile

def makeProjectLabel(configuration, path):
    if configuration["title"] != "":
        # Tester si les metadonées contiennent un titre
        usedName=configuration["title"]
    else:
        # Sinon, se servir du nom du fichier
        head, tail = os.path.split(path)
        usedName=tail

    # Unicode à ascii
    usedName = unicodedata.normalize('NFKD', usedName).encode('ascii', 'ignore')
    # Tout en minuscule
    usedName = usedName.lower()
    # les espaces devienent des tirets
    usedName = usedName.decode('UTF-8').replace(' ', '-')

    return usedName

def setProjectLabel(configuration, path):
    global ProjectLabel
    ProjectLabel = makeProjectLabel(configuration, path)


def defineFinalOutputFile():
    global ProjectLabel
    global FinalFileName
    FinalFileName=tempfile.NamedTemporaryFile(delete=False, mode='w+b', prefix=progname+"-"+ProjectLabel, suffix="-fullcover"+".pdf")

def defineNewSetOfTemporaryFiles():
    global FirstPageFileName
    global LastPageFileName
    global FinalFileName

    FirstPageFileName = prepareTemporaryFile("first")
    LastPageFileName = prepareTemporaryFile("last")
    FinalFileName =  prepareTemporaryFile("final")

    print("==================")
    print(FirstPageFileName.name)
    print(LastPageFileName.name)
    print(FinalFileName.name)

def on_file_selected():
    # Procéssus à enclencher dès le click sur le bouton de selection de pdf
    try:
        win.buttonCreate.set_sensitive(False)
        filename=win.fileChooser.get_filename()
        defineNewSetOfTemporaryFiles()
        info=pdfTreatment(filename)
        print("truc")
        setLeftEntry(info)
        setCenterEntry(info)
        setRightEntry(info)
        print(info["color"])
        win.buttonSelectSpinColor.set_color(info["color"])

        print("Finish pdf import")
        global ProjectLabel
        print(ProjectLabel)
        finalMessage("Import achevé")
        win.buttonCreate.set_sensitive(True)
    except:
        finalMessage("Someting wrong happend")


def getUnitLabelFromIndex(index):
    # Récupération de l’unité choisie pour la tranche
    return listOfUnits[index]

def getChoosenParameters():
    # Préparation de la configuration suggérée pour le PDF en entrée.
    configuration = {
        "path"           : win.fileChooser.get_filename(),
        "color"          : win.buttonSelectSpinColor.get_color(),
        "left"           : win.entryLeftInscription.get_text(),
        "center"         : win.entryCenterInscription.get_text(),
        "right"          : win.entryRightInscription.get_text(),
        "spinWidth"      : win.inputWidthSelector.get_text(),
        "unit"           : getUnitLabelFromIndex(win.inputUnitStore.get_active()),
        "pdfWidth"       : info["pdfWidth"],
        "pdfHeight"      : info["pdfHeight"],
        "pageNumber"     : info["pageNumber"],
        "orientation"    : win.buttonSelectSide.get_active(),
        "forgroundColor" : setForegroundColor(win.buttonSelectSpinColor.get_color())
    }

    return configuration


def buildTheTexProject(configuration):
    # Enclenchement du procéssus TeX, avec création des sources et compilation

    global FinalFileName
    TeXfile=makeTheTeXfile(configuration)
    #print(TeXfile)
    outputpdf = build_pdf(TeXfile)
    outputpdf.save_to(FinalFileName.name)

def createTheCover_no_lag(widget):
    # Fonction d’enclenchement du procéssus de création de couverture.
    # ne fait qu’encapsuler createTheCover() afin que l’application ne freeze pas durant le procéssus.
    t = threading.Thread(name='Creating letter', target=createTheCover)
    t.start()

# TODO suprimer `widget` comme paramettre lorsqu’utilisé avec no_lag
def createTheCover(widget):
    # Enclenchement du procéssus à proprement parler

    global FinalFileName
    print("enter createTheCover()")
    configuration=getChoosenParameters()
    print(configuration)
    buildTheTexProject(configuration)
    openPdfFile(FinalFileName.name)



win = GridWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
