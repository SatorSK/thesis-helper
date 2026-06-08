"""python-docx 에 실제 각주(footnote)를 넣는 엔진.

python-docx 는 각주를 기본 지원하지 않으므로 OOXML 파트를 직접 주입한다.
Word 가 페이지 하단 각주로 렌더링한다.

사용법:
    mgr = FootnoteManager(document)
    mgr.add(paragraph, "각주 텍스트")   # 본문 곳곳에서 호출
    mgr.finalize()                       # 저장 직전 한 번
실패하면 예외를 던지므로 호출부에서 윗첨자+미주 목록으로 폴백할 수 있다.
"""
from __future__ import annotations

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from lxml import etree


def _serialize(element) -> bytes:
    return etree.tostring(element, xml_declaration=True, encoding="UTF-8", standalone=True)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
FOOTNOTES_CT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
)

_DEFAULT_FOOTNOTES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:footnotes xmlns:w="{W}">'
    '<w:footnote w:type="separator" w:id="-1">'
    '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
    '<w:r><w:separator/></w:r></w:p></w:footnote>'
    '<w:footnote w:type="continuationSeparator" w:id="0">'
    '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
    '<w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
    '</w:footnotes>'
)


class FootnoteManager:
    def __init__(self, document):
        self.document = document
        self._root = parse_xml(_DEFAULT_FOOTNOTES.encode("utf-8"))
        self._next_id = 1
        self._finalized = False

    def add(self, paragraph, text: str) -> int:
        fid = self._next_id
        self._next_id += 1

        # 1) 각주 본문(footnotes.xml 의 한 항목)
        fn = OxmlElement("w:footnote")
        fn.set(qn("w:id"), str(fid))
        p = OxmlElement("w:p")
        r_ref = OxmlElement("w:r")
        rpr_ref = OxmlElement("w:rPr")
        va = OxmlElement("w:vertAlign")
        va.set(qn("w:val"), "superscript")
        rpr_ref.append(va)
        r_ref.append(rpr_ref)
        r_ref.append(OxmlElement("w:footnoteRef"))
        p.append(r_ref)
        r_txt = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = " " + (text or "")
        r_txt.append(t)
        p.append(r_txt)
        fn.append(p)
        self._root.append(fn)

        # 2) 본문에 각주 참조 run
        run = paragraph.add_run()
        rpr = run._r.get_or_add_rPr()
        va2 = OxmlElement("w:vertAlign")
        va2.set(qn("w:val"), "superscript")
        rpr.append(va2)
        ref = OxmlElement("w:footnoteReference")
        ref.set(qn("w:id"), str(fid))
        run._r.append(ref)
        return fid

    def finalize(self):
        """저장 직전 호출: footnotes 파트를 생성·연결한다."""
        if self._finalized:
            return
        blob = _serialize(self._root)
        partname = PackURI("/word/footnotes.xml")
        part = Part(partname, FOOTNOTES_CT, blob, self.document.part.package)
        self.document.part.relate_to(part, RT.FOOTNOTES)
        self._finalized = True
