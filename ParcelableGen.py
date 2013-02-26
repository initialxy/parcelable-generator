"""
Copyright (C) 2013 initialxy and other contributors
http://code.google.com/p/parcelable-generator/

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
A utility to generate Java codes in order to make a class Parcelable. Run this
script with
>> python ParcelableGen.py
Copy and paste your Java class into stdin, signify end of file (ctrl+z on
windows or ctrl+d on *nix), then press enter. Java codes will be printed to
stdout. Copy and paste generated code into your Java file. You probably want to
press shift+ctrl+o then shift+ctrl+f in Eclipse afterwards. It could make
mistakes, so sometimes manual editing is required. For one, it cannot correctly
detect enums (it's not that smart). It detects enums by checking if type name
ends with "Type". If it gets wrong, you might want to temporarily change type
name (either add or remove "Type" from its end), generate, then manually
correct type name. But it still makes your life much easier.
"""

import sys
import re
import abc

CLASS_REGEX = re.compile(r"^\s*public (static |)(abstract |)class\s+(\S+)\s+.*")
MEMBER_REGEX = re.compile(r"^\s*(public|private)\s+(\S+)\s+(\S+)\;.*")

PREFERED_LIST_TYPE = "ArrayList"

ENUM_TYPE_NAMING_SCHEME = re.compile(r".+Type")

TEMPLATE = """
    /**************************************************************************
     * Code to make this class Parcelable. Generated by ParcelableGen.py
     */

    public static final Parcelable.Creator<{{className}}> CREATOR = new Creator();

    /**
     * Default constructor, needed for Jackson. Remove if necessary.
     */
    public {{className}}() {
    }

    /**
     * Reconstruct from Parcel
     */
    public {{className}}(Parcel in) {
{{read}}
    }

    @Override
    public void writeToParcel(Parcel out, int flags) {
{{write}}
    }

    @Override
    public int describeContents() {
        return 0;
    }

    private static class Creator implements Parcelable.Creator<{{className}}> {
        public {{className}} createFromParcel(Parcel source) {
            return new {className}(source);
        }

        public {{className}}[] newArray(int size) {
            return new {className}[size];
        }
    }

    /**************************************************************************
     * Parcelable codes end
     */
    """

class Generator(object):
    def __init__(self):
        self.template = ""
        self.indentation = ""
        self.tab = ""
        self.className = ""
        self.members = []
        self.adapters = []
        self.defaultAdapter = None;

    def setTemplate(self, template, indentation, tab):
        self.template = template;
        self.indentation = indentation;
        self.tab = tab;

    def setClassName(self, className):
        self.className = className;

    def addMember(self, dataType, name):
        self.members.append((dataType, name))

    def addAdapter(self, adapter):
        self.adapters.append(adapter)

    def setDefaultAdapter(self, adapter):
        self.defaultAdapter = adapter

    def gen(self):
        out = self.template.replace("{{className}}", self.className)

        # To be used as string builders.
        read = []
        write = []

        for m in self.members:
            isAdapterFound = False
            for a in self.adapters:
                n = a.getSupportedType().match(m[0])
                if n:
                    isAdapterFound = True
                    read += a.genRead(m[0], m[1]).split("\n")
                    write += a.genWrite(m[0], m[1]).split("\n")

            if not isAdapterFound:
                if self.defaultAdapter is not None:
                    # If none of the registered adapters are suitable, use
                    # default.
                    read.append(self.defaultAdapter.genRead(m[0], m[1]))
                    write.append(self.defaultAdapter.genWrite(m[0], m[1]))
                else :
                    sys.stderr.write(m[0] + " " + m[1] \
                            + " is ignored, because no suitable adapter " \
                            + "is found.\n")

        # Add indentation.
        read = self.__formatIndentation(read)
        write = self.__formatIndentation(write)

        out = out.replace("{{read}}", "".join(read))
        out = out.replace("{{write}}", "".join(write))

        print out

    def __formatIndentation(self, lines):
        """Responsible for making corrections for indentation"""
        curSep = ""
        sep = "\n"
        additionalTabs = 0

        for i in range(len(lines)):
            # Strip first
            lines[i] = lines[i].strip()

            curAdditionalTabs = additionalTabs

            openingBracketNum = 0
            closingBracketNum = 0

            # We need to count the number of closing brackets before opening
            # brackets and delete that many number of tabs for current line.
            # While at it also count the number of opening brackets and
            # closing brackets. We will use one iteration for this.
            for c in lines[i]:
                if c == "{":
                    openingBracketNum += 1
                if c == "}":
                    closingBracketNum += 1
                    if openingBracketNum <= 0:
                        curAdditionalTabs -= 1

            if curAdditionalTabs < 0:
                curAdditionalTabs = 0;

            additionalTabs += openingBracketNum
            additionalTabs -= closingBracketNum

            lines[i] = curSep + self.indentation \
                    + (self.tab * curAdditionalTabs) + lines[i]
            curSep = sep

        return lines

class ConfiguredGenerator(Generator):
    """Sets up all of the adapters in constructor"""

    SUPPORTED_TYPES = ["byte", "double", "float", "int", "long", "String",
            "java.lang.String", "boolean[]", "byte[]", "char[]", "double[]", 
            "float[]", "int[]", "long[]", "String[]"]

    SUPPORTED_TYPES_METHOD_NAMES = ["Byte", "Double", "Float", "Int", "Long",
            "String", "String", "BooleanArray", "ByteArray", "CharArray",
            "DoubleArray", "FloatArray", "IntArray", "longArray", "StringArray"]

    def __init__(self):
        super(ConfiguredGenerator, self).__init__()
        self.setTemplate(TEMPLATE, " " * 8, " " * 4)

        self.setDefaultAdapter(ParcelableAdapter())

        for i in range(len(self.SUPPORTED_TYPES)):
            self.addAdapter(NativeTypeAdapter(re.compile(
                    self.SUPPORTED_TYPES[i] \
                    .replace("[", "\\[").replace("]", "\\]")),
                    self.SUPPORTED_TYPES_METHOD_NAMES[i]))

        self.addAdapter(PrimitiveBooleanAdapter())
        self.addAdapter(ListAdapter(PREFERED_LIST_TYPE))
        self.addAdapter(EnumAdapter(ENUM_TYPE_NAMING_SCHEME))
        self.addAdapter(CalendarAdapter())
        self.addAdapter(GregorianCalendarAdapter())
        self.addAdapter(XMLGregorianCalendarAdapter())

class Adapter(object):
    @abc.abstractmethod
    def getSupportedType(self):
        "Returns supported dataType as a compiled regex."
        return

    @abc.abstractmethod
    def genRead(self, dataType, name):
        """Given dataType and name, generate Parcelable read codes
        (in.read.*) as a string, don't worry about indentation."""
        return

    @abc.abstractmethod
    def genWrite(self, dataType, name):
        """Given dataType and name, generate Parcelable write codes
        (out.write.*). don't worry about indentation."""
        return

class TemplateAdapter(Adapter):
    """Use this adapter serves as a base class for anything that simply needs
    to put dataType and name into a template."""

    @abc.abstractmethod
    def getReadTemplate(self):
        """Return read code template."""
        return

    @abc.abstractmethod
    def getWriteTemplate(self):
        """Return write code template."""
        return

    def genRead(self, dataType, name):
        return self.getReadTemplate() \
                .replace("{{dataType}}", dataType).replace("{{name}}", name)

    def genWrite(self, dataType, name):
        return self.getWriteTemplate() \
                .replace("{{dataType}}", dataType).replace("{{name}}", name)

class NativeTypeAdapter(Adapter):
    """Use this adapter for any of the primitive types that's natively
    supported by Parcel."""

    def __init__(self, supportedType, typeMethodNameSuffix):
        """supportedType is expected to be compiled regex"""
        self.supportedType = supportedType
        self.typeMethodNameSuffix = typeMethodNameSuffix

    def getSupportedType(self):
        return self.supportedType

    def genRead(self, dataType, name):
        return name + " = in.read" + self.typeMethodNameSuffix + "();"

    def genWrite(self, dataType, name):
        return "out.write" + self.typeMethodNameSuffix + "(" + name + ");"

class ParcelableAdapter(TemplateAdapter):
    """Use this adapter for Parcelable type. This adapter really should be
    used as default adapter."""

    def getSupportedType(self):
        return re.compile(r".*Parcelable")

    def getReadTemplate(self):
        return """{{dataType}} = in.readParcelable({{name}}.class.getClassLoader());"""

    def getWriteTemplate(self):
        return """out.writeParcelable({{name}}, 0);"""

class PrimitiveBooleanAdapter(TemplateAdapter):
    """Use this adapter for primitive boolean type."""

    def getSupportedType(self):
        return re.compile(r"boolean")

    def getReadTemplate(self):
        return """boolean[] {{name}}Array = new boolean[1];
            in.readBooleanArray({{name}}Array);
            {{name}} = {{name}}Array[0];"""

    def getWriteTemplate(self):
        return """out.writeBooleanArray(new boolean[] { {{name}} });"""

class ListAdapter(Adapter):
    """Use this adapter for any of the List types."""

    GENERICS_REGEX = re.compile(r"\s*(\S+)\<(.+)\>.*")

    READ_TEMPLATE = """{{name}} = new {{listType}}<{{genericType}}>();
            in.readList({{name}}, {{genericType}}.class.getClassLoader());"""
    WRITE_TEMPLATE = """out.writeList({{name}});"""

    def __init__(self, preferredListType):
        self.preferredListType = preferredListType

    def getSupportedType(self):
        return re.compile(r".*List")

    def genRead(self, dataType, name):
        genericType = ""
        listType = ""

        m = self.GENERICS_REGEX.match(dataType)
        if m:
            genericType = m.group(2)
            listType = m.group(1)
        else:
            listType = dataType

        if listType == "" or listType == "List" or listType == "java.util.List":
            listType = self.preferredListType

        return self.READ_TEMPLATE.replace("{{name}}", name) \
                .replace("{{listType}}", listType) \
                .replace("{{genericType}}", genericType)

    def genWrite(self, dataType, name):
        return self.WRITE_TEMPLATE.replace("{{name}}", name) \
                .replace("{{dataType}}", dataType)

class EnumAdapter(TemplateAdapter):
    """Use this adapter for primitive enum type. Note that it depends on a
    consistent enum type naming scheme to identify enums."""

    def __init__(self, enumTypeNamingScheme):
        self.enumTypeNamingScheme = enumTypeNamingScheme

    def getSupportedType(self):
        return self.enumTypeNamingScheme

    def getReadTemplate(self):
        return """String {{name}}Str = in.readString();
            if ({{name}}Str != null) {
                {{name}} = {{dataType}}.valueOf({{name}}Str);
            } else {
                {{name}} = null;
            }"""

    def getWriteTemplate(self):
        return """if ({{name}} != null) {
                out.writeString({{name}}.name());
            } else {
                out.writeString(null);
            }"""

class CalendarAdapter(TemplateAdapter):
    """Use this adapter for Calendar type."""

    def getSupportedType(self):
        return re.compile(r"(.+\.|)(Calendar)")

    def getReadTemplate(self):
        return """String {{name}}TimeZoneStr = in.readString();
            if ({{name}}TimeZoneStr != null) {
                {{name}} = Calendar.getInstance();
                {{name}}.setTimeZone(TimeZone.getTimeZone({{name}}TimeZoneStr));
                {{name}}.setTimeInMillis(in.readLong());
            } else {
                {{name}} = null;
            }"""

    def getWriteTemplate(self):
        return """if ({{name}} != null) {
                out.writeString({{name}}.getTimeZone().getID());
                out.writeLong({{name}}.getTimeInMillis());
            } else {
                out.writeString(null);
            }"""

class GregorianCalendarAdapter(CalendarAdapter):
    """Use this adapter for GregorianCalenar type."""

    def getSupportedType(self):
        return re.compile(r"(.+\.|)(GregorianCalendar)")

    def getReadTemplate(self):
        return """String {{name}}TimeZoneStr = in.readString();
            if ({{name}}TimeZoneStr != null) {
                {{name}} = new GregorianCalendar(TimeZone.getTimeZone({{name}}TimeZoneStr));
                {{name}}.setTimeInMillis(in.readLong());
            } else {
                {{name}} = null;
            }"""

class XMLGregorianCalendarAdapter(TemplateAdapter):
    """Use this adapter for XMLGregorianCalenar type."""

    def getSupportedType(self):
        return re.compile(r"(.+\.|)(XMLGregorianCalendar)")

    def getReadTemplate(self):
        return """try {
                {{name}} = javax.xml.datatype.DatatypeFactory.newInstance().newXMLGregorianCalendar(in.readString());
            } catch (DatatypeConfigurationException dce) {}"""

    def getWriteTemplate(self):
        return """out.writeString({{name}}.toString());"""

def main():
    lines = sys.stdin.readlines()
    gen = ConfiguredGenerator()

    for line in lines:
        m = MEMBER_REGEX.match(line)

        if m:
            gen.addMember(m.group(2), m.group(3))
            continue;

        m = CLASS_REGEX.match(line)
        
        if m:
            gen.setClassName(m.group(3))
            continue

    gen.gen()

main()

