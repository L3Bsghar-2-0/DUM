import zipfile
import xml.etree.ElementTree as ET

docx_path = r"c:\Users\Mega Pc\DUM\data\ReTeqFusion Final.docx"
content = []

try:
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        xml_content = zip_ref.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for text_elem in root.findall('.//w:t', namespace):
            if text_elem.text:
                content.append(text_elem.text)
    
    output_path = r"c:\Users\Mega Pc\DUM\data\ReTeqFusion_extracted.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(content))
    
    print(f"✅ Successfully extracted to {output_path}")
    print(f"📄 Content length: {len(''.join(content))} characters")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
