#!/usr/bin/env python

#
# xliff-export.py l10n-repository export-directory
#
# Convert the l10n repository from the following format:
#
#  en/firefox-ios.xliff
#  fr/firefox-ios.xliff
#
# To the following format:
#
#  Client/en-US.lproj/Localizable.strings
#  Client/fr.lproj/Localizable.strings
#  ShareTo/en-US.lproj/ShareTo.strings
#  ShareTo/fr.lproj/ShareTo.strings
#  SendTo/en-US.lproj/SendTo.strings
#  SendTo/fr.lproj/SendTo.strings
#
# For any Info.plist file in the xliff, we generate a InfoPlist.strings.
#

import glob
import os
import sys

from lxml import etree

NS = {'x':'urn:oasis:names:tc:xliff:document:1.2'}

# Files we are interested in. It would be nice to not hardcode this but I'm not totally sure how yet.
FILES = [
    "Client/BookmarkPanel.strings",
    "Client/ClearPrivateData.strings",
    "Client/ErrorPages.strings",
    "Client/HistoryPanel.strings",
    "Client/Info.plist",
    "Client/Intro.strings",
    "Client/Localizable.strings",
    "Client/Search.strings",
    "Extensions/SendTo/Info.plist",
    "Extensions/SendTo/SendTo.strings",
    "Extensions/ShareTo/ShareTo.strings",
    "Shared/Localizable.strings",
]

# Because Xcode is unpredictable. See bug 1162510 - Sync.strings are not imported
FILENAME_OVERRIDES = {
    "Shared/Supporting Files/Info.plist": "Shared/Localizable.strings",
}

def export_xliff_file(file_node, export_path, target_language):
    directory = os.path.dirname(export_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(export_path, "w") as fp:
        for trans_unit_node in file_node.xpath("x:body/x:trans-unit", namespaces=NS):
            trans_unit_id = trans_unit_node.get("id")
            targets = trans_unit_node.xpath("x:target", namespaces=NS)

            if trans_unit_id is not None and len(targets) == 1 and targets[0].text is not None:
                notes = trans_unit_node.xpath("x:note", namespaces=NS)
                if len(notes) == 1:
                    line = u"/* %s */\n" % notes[0].text
                    fp.write(line.encode("utf8"))
                source_text = trans_unit_id.replace("'", "\\'")
                target_text = targets[0].text.replace("'", "\\'")
                line = u"\"%s\" = \"%s\";\n\n" % (source_text, target_text)
                fp.write(line.encode("utf8"))

    # Export fails if the strings file is empty. Xcode probably checks
    # on file length vs read error.
    contents = open(export_path).read()
    if len(contents) == 0:
        os.remove(export_path)

def original_path(root, target, original):
    dir,file = os.path.split(original)
    if file == "Info.plist":
        file = "InfoPlist.strings"
    lproj = "%s.lproj" % target_language
    path = dir + "/" + lproj + "/" + file
    return path

if __name__ == "__main__":

    import_root = sys.argv[1]
    if not os.path.isdir(import_root):
        print "import path does not exist or is not a directory"
        sys.exit(1)

    export_root = sys.argv[2]
    if not os.path.isdir(export_root):
        print "export path does not exist or is not a directory"
        sys.exit(1)

    for xliff_path in glob.glob(import_root + "/*/firefox-ios.xliff"):
        print "Exporting", xliff_path
        with open(xliff_path) as fp:
            tree = etree.parse(fp)
            root = tree.getroot()

            # Make sure there are <file> nodes in this xliff file.
            file_nodes = root.xpath("//x:file", namespaces=NS)
            if len(file_nodes) == 0:
                print "  ERROR: No translated files. Skipping."
                continue

            # Take the target language from the first <file>. Not sure if that
            # is a bug in the XLIFF, but in some files only the first node has
            # the target-language set.
            target_language = file_nodes[0].get('target-language')
            if not target_language:
                print "  ERROR: Missing target-language. Skipping."
                continue

            # Export each <file> node as a separate strings file under the
            # export root.
            for file_node in file_nodes:
                original = file_node.get('original')
                original = FILENAME_OVERRIDES.get(original, original)
                if original in FILES:
                    export_path = original_path(export_root, target_language, original)
                    print "  Writing", export_path, target_language
                    export_xliff_file(file_node, export_path, target_language)
