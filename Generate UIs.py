from defusedxml import ElementTree
from pathlib import Path
from subprocess import run  #nosec
ui_dir = "./"
output_dir = "./"

InputFiles = Path(ui_dir).glob('*.[uq][ir]*')
for InputFile in InputFiles:
    OutputFileName=""
    if(str(InputFile).endswith('.ui')):
        ClassName = ElementTree.parse(InputFile).getroot()[0].text
        OutputFileName = "ui_" + ClassName.lower() + ".py"
        run(["pyside6-uic", InputFile, "-o",
            output_dir+OutputFileName, "--from-imports"])
    elif(str(InputFile).endswith('.qrc')):
        OutputFileName=InputFile.name[:-4]+'_rc.py'
        run(["pyside6-rrc", InputFile, "-o", output_dir+OutputFileName])

    print(OutputFileName)
    
