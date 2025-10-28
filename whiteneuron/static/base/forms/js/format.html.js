/**
 * Pretty-print an HTML string for display to users.
 * - Parse bằng DOMParser thay vì regex.
 * - Tôn trọng vùng giữ khoảng trắng: <pre>, <code>, <textarea>.
 * - Không thêm thừa thãi closing tag cho void elements.
 * - Thu gọn text node thừa khoảng trắng (trừ vùng preserve).
 * - Tuỳ chọn: kích thước thụt lề, bỏ comment, giữ nguyên doctype.
 */
function formatHtml(input, options = {}) {
  if (!input || typeof input !== 'string') return '';

  const {
    indent = 2,
    removeComments = false,
    keepDoctype = true,
  } = options;

  const INDENT = ' '.repeat(indent);

  const VOID = new Set([
    'area','base','br','col','embed','hr','img','input','link',
    'meta','param','source','track','wbr'
  ]);

  const PRESERVE_WS = new Set(['pre', 'code', 'textarea']);

  // Heuristic block/inline để xuống dòng hợp lý
  const BLOCK = new Set([
    'html','head','body','article','section','nav','aside','header','footer','main',
    'div','p','h1','h2','h3','h4','h5','h6','blockquote','figure','figcaption',
    'ul','ol','li','dl','dt','dd','table','thead','tbody','tfoot','tr','td','th',
    'form','fieldset','legend','details','summary','hr'
  ]);

  // Parse
  const parser = new DOMParser();
  const doc = parser.parseFromString(input, 'text/html');

  // Doctype
  let out = '';
  if (keepDoctype && doc.doctype) {
    out += `<!DOCTYPE ${doc.doctype.name}${
      doc.doctype.publicId ? ` PUBLIC "${doc.doctype.publicId}"` : ''
    }${doc.doctype.systemId ? ` "${doc.doctype.systemId}"` : ''}>\n`;
  }

  // Main entry: prefer <html>, fallback to body’s children if parser wrapped
  const root = doc.documentElement || doc.body;

  const escapeText = (str) =>
    str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  const escapeAttr = (str) =>
    String(str)
      .replace(/&/g,'&amp;')
      .replace(/"/g,'&quot;')
      .replace(/</g,'&lt;');

  const serializeAttrs = (el) => {
    if (!el.hasAttributes()) return '';
    // Duy trì thứ tự thuộc tính như DOM hiện có
    const parts = [];
    for (const attr of el.attributes) {
      // Bỏ thuộc tính rỗng kiểu boolean? Ta vẫn giữ: disabled="", checked=""
      parts.push(`${attr.name}="${escapeAttr(attr.value)}"`);
    }
    return parts.length ? ' ' + parts.join(' ') : '';
  };

  const isWhitespaceOnly = (s) => /^[\t\n\r ]*$/.test(s);

  function walk(node, depth, inPreserve) {
    switch (node.nodeType) {
      case Node.ELEMENT_NODE: {
        const el = /** @type {HTMLElement} */ (node);
        const tag = el.tagName.toLowerCase();
        const preserveHere = inPreserve || PRESERVE_WS.has(tag);
        const isBlock = BLOCK.has(tag);

        const open = `<${tag}${serializeAttrs(el)}${VOID.has(tag) ? '' : '>'}`;
        const close = VOID.has(tag) ? '' : `</${tag}>`;

        let lineStart = INDENT.repeat(depth);
        if (isBlock && out[out.length - 1] !== '\n') out += '\n';
        out += lineStart + open;

        if (VOID.has(tag)) {
          out += (isBlock ? '\n' : '');
          return;
        }

        // Children
        let hadElementChild = false;
        for (const child of el.childNodes) {
          if (child.nodeType === Node.ELEMENT_NODE) {
            hadElementChild = true;
            walk(child, depth + 1, preserveHere);
          } else if (child.nodeType === Node.TEXT_NODE) {
            const raw = child.nodeValue || '';
            if (preserveHere) {
              // Giữ nguyên (nhưng không ép thêm indent để không phá code/pre)
              out += raw;
            } else {
              // Thu gọn khoảng trắng giữa các block/inline bình thường
              const collapsed = raw.replace(/\s+/g, ' ');
              if (!isWhitespaceOnly(collapsed)) {
                out += escapeText(collapsed.trim());
              }
            }
          } else if (child.nodeType === Node.COMMENT_NODE) {
            if (!removeComments) {
              const comment = child.nodeValue || '';
              if (preserveHere) {
                out += `<!--${comment}-->`;
              } else {
                out += `\n${INDENT.repeat(depth + 1)}<!-- ${comment.trim()} -->`;
              }
            }
          }
        }

        // Đóng thẻ
        if (hadElementChild || (isBlock && !preserveHere)) {
          if (!out.endsWith('\n')) out += '\n';
          out += INDENT.repeat(depth) + close + '\n';
        } else {
          // Không có element con: đóng liền hoặc gọn gàng cùng dòng
          out += close;
          out += (isBlock ? '\n' : '');
        }
        return;
      }

      case Node.TEXT_NODE: {
        const txt = node.nodeValue || '';
        if (inPreserve) {
          out += txt;
        } else {
          const collapsed = txt.replace(/\s+/g, ' ');
          if (!isWhitespaceOnly(collapsed)) {
            out += escapeText(collapsed.trim());
          }
        }
        return;
      }

      case Node.COMMENT_NODE: {
        if (!removeComments) {
          const comment = node.nodeValue || '';
          out += `\n${INDENT.repeat(depth)}<!-- ${comment.trim()} -->\n`;
        }
        return;
      }

      default:
        return;
    }
  }

  // Nếu có <html>, đi từ đó; nếu không, đi qua body children để đỡ in <html><head>… khi user chỉ đưa mảnh HTML
  if (doc.documentElement && (/<(html|head|body)\b/i).test(input)) {
    walk(doc.documentElement, 0, false);
  } else {
    for (const n of doc.body.childNodes) walk(n, 0, false);
    if (!out.endsWith('\n')) out += '\n';
  }

  // Làm gọn dòng trống kép
  out = out.replace(/\n{3,}/g, '\n\n').trim() + '\n';
  return out;
}
