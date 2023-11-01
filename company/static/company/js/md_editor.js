// -------------------------------------------
// DEFAULT INPUT AND OUTPUT AREA
let textarea = document.querySelector('#input-area');
let outputArea = document.querySelector('#output-area');
let previewMessage = document.querySelector('.preview-message');

// -------------------------------------------
// TOOLBAR
// -------------------------------------------
const preview = document.querySelector('#preview');
const boldButton = document.querySelector('#bold');
const italicButton = document.querySelector('#italic');
const heading1Button = document.querySelector('#heading1');
const heading2Button = document.querySelector('#heading2');
const heading3Button = document.querySelector('#heading3');
const linkButton = document.querySelector('#link');
const tokenButton = document.querySelector('#token');
const ulButton = document.querySelector('#list-ul');
const olButton = document.querySelector('#list-ol');


preview.addEventListener('click', () => {
    output(escapeHTML(parse(textarea.value)));

    outputArea.classList.toggle('show');
    previewMessage.classList.toggle('show');
    preview.classList.toggle('active');
});

boldButton.addEventListener('click', () =>
    insertText(textarea, '****', 'demo', 2, 6)
);

italicButton.addEventListener('click', () =>
    insertText(textarea, '**', 'demo', 1, 5)
);

heading1Button.addEventListener('click', () =>
    insertText(textarea, '#', 'heading1', 1, 9)
);

heading2Button.addEventListener('click', () =>
    insertText(textarea, '##', 'heading2', 2, 10)
);

heading3Button.addEventListener('click', () =>
    insertText(textarea, '###', 'heading3', 3, 11)
);

linkButton.addEventListener('click', () =>
    insertText(textarea, '[](http://...)', 'url text', 1, 9)
);

tokenButton.addEventListener('click', () =>
    insertText(textarea, '{{}}', 'tokenValue', 2, 12)
);

ulButton.addEventListener('click', function () {
    insertText(textarea, '* ', 'item', 2, 6);
});

olButton.addEventListener('click', () =>
    insertText(textarea, '1. ', 'item', 3, 7)
);

// -------------------------------------------

function setInputArea(inputElement) {
    textarea = inputElement;
}

function setOutputArea(outputElement) {
    outputArea = outputElement;
}

function insertText(textarea, syntax, placeholder = 'demo', selectionStart = 0, selectionEnd = 0) {
    // Current Selection
    const currentSelectionStart = textarea.selectionStart;
    const currentSelectionEnd = textarea.selectionEnd;
    const currentText = textarea.value;

    if (currentSelectionStart === currentSelectionEnd) {
        const textWithSyntax = textarea.value = currentText.substring(0, currentSelectionStart) + syntax + currentText.substring(currentSelectionEnd);
        textarea.value = textWithSyntax.substring(0, currentSelectionStart + selectionStart) + placeholder + textWithSyntax.substring(currentSelectionStart + selectionStart)

        textarea.focus();
        textarea.selectionStart = currentSelectionStart + selectionStart;
        textarea.selectionEnd = currentSelectionEnd + selectionEnd;
    } else {
        const selectedText = currentText.substring(currentSelectionStart, currentSelectionEnd);
        const withoutSelection = currentText.substring(0, currentSelectionStart) + currentText.substring(currentSelectionEnd);
        const textWithSyntax = withoutSelection.substring(0, currentSelectionStart) + syntax + withoutSelection.substring(currentSelectionStart);

        // Surround selected text
        textarea.value = textWithSyntax.substring(0, currentSelectionStart + selectionStart) + selectedText + textWithSyntax.substring(currentSelectionStart + selectionStart);

        textarea.focus();
        textarea.selectionEnd = currentSelectionEnd + selectionStart + selectedText.length;
    }
}

function output(lines) {
    outputArea.innerHTML = lines;
}

// -------------------------------------------
// PARSER
// -------------------------------------------

function parse(content) {
    // Regular Expressions
    const h1 = /^#{1}[^#].*$/gm;
    const h2 = /^#{2}[^#].*$/gm;
    const h3 = /^#{3}[^#].*$/gm;
    const bold = /\*\*[^\*\n]+\*\*/gm;
    const italics = /[^\*]\*[^\*\n]+\*/gm;
    const link = /\[[\w|\(|\)|\s|\*|\?|\-|\.|\,]*(\]\(){1}[^\)]*\)/gm;
    const lists = /^((\s*((\*|\-)|\d(\.|\))) [^\n]+))+$/gm;
    const unorderedList = /^[\*|\+|\-]\s.*$/;
    const unorderedSubList = /^\s\s\s*[\*|\+|\-]\s.*$/;
    const orderedList = /^\d\.\s.*$/;
    const orderedSubList = /^\s\s+\d\.\s.*$/;

    // Example: # Heading 1
    if (h1.test(content)) {
        const matches = content.match(h1);

        matches.forEach(element => {
            const extractedText = element.slice(1);
            content = content.replace(element, '<h1 class="text-4xl font-bold">' + extractedText + '</h1>');
        });
    }

    // Example: # Heading 2
    if (h2.test(content)) {
        const matches = content.match(h2);

        matches.forEach(element => {
            const extractedText = element.slice(2);
            content = content.replace(element, '<h2 class="text-3xl font-semibold">' + extractedText + '</h2>');
        });
    }

    // Example: # Heading 3
    if (h3.test(content)) {
        const matches = content.match(h3);

        matches.forEach(element => {
            const extractedText = element.slice(3);
            content = content.replace(element, '<h3 class="text-2xl font-medium">' + extractedText + '</h3>');
        });
    }

    // Example: **Bold**
    if (bold.test(content)) {
        const matches = content.match(bold);

        matches.forEach(element => {
            const extractedText = element.slice(2, -2);
            content = content.replace(element, '<strong class="font-bold">' + extractedText + '</strong>');
        });
    }

    // Example: *Italic*
    if (italics.test(content)) {
        const matches = content.match(italics);

        matches.forEach(element => {
            const extractedText = element.slice(2, -1);
            content = content.replace(element, ' <em class="italic">' + extractedText + '</em>');
        });
    }

    // Example: [I'm an inline-style link](https://www.google.com)
    if (link.test(content)) {
        const links = content.match(link);

        links.forEach(element => {
            const text = element.match(/^\[.*\]/)[0].slice(1, -1);
            const url = element.match(/\]\(.*\)/)[0].slice(2, -1);

            content = content.replace(element, '<a class="text-blue-500 underline" href="' + url + '">' + text + '</a>');
        });
    }

    if (lists.test(content)) {
        const matches = content.match(lists);

        matches.forEach(list => {
            const listArray = list.split('\n');

            const formattedList = listArray.map((currentValue, index, array) => {
                if (unorderedList.test(currentValue)) {
                    currentValue = '<li>' + currentValue.slice(2) + '</li>';

                    if (!unorderedList.test(array[index - 1]) && !unorderedSubList.test(array[index - 1])) {
                        currentValue = '<ul class="list-disc pl-4">' + currentValue;
                    }

                    if (!unorderedList.test(array[index + 1]) && !unorderedSubList.test(array[index + 1])) {
                        currentValue = currentValue + '</ul>';
                    }

                    if (unorderedSubList.test(array[index + 1]) || orderedSubList.test(array[index + 1])) {
                        currentValue = currentValue.replace('</li>', '');
                    }
                }

                if (unorderedSubList.test(currentValue)) {
                    currentValue = currentValue.trim();
                    currentValue = '<li>' + currentValue.slice(2) + '</li>';

                    if (!unorderedSubList.test(array[index - 1])) {
                        currentValue = '<ul>' + currentValue;
                    }

                    if (!unorderedSubList.test(array[index + 1]) && unorderedList.test(array[index + 1])) {
                        currentValue = currentValue + '</ul></li>';
                    }

                    if (!unorderedSubList.test(array[index + 1]) && !unorderedList.test(array[index + 1])) {
                        currentValue = currentValue + '</ul></li></ul>';
                    }
                }

                if (orderedList.test(currentValue)) {
                    currentValue = '<li>' + currentValue.slice(2) + '</li>';

                    if (!orderedList.test(array[index - 1]) && !orderedSubList.test(array[index - 1])) {
                        currentValue = '<ol class="list-decimal pl-4">' + currentValue;
                    }

                    if (!orderedList.test(array[index + 1]) && !orderedSubList.test(array[index + 1]) && !orderedList.test(array[index + 1])) {
                        currentValue = currentValue + '</ol>';
                    }

                    if (unorderedSubList.test(array[index + 1]) || orderedSubList.test(array[index + 1])) {
                        currentValue = currentValue.replace('</li>', '');
                    }
                }

                if (orderedSubList.test(currentValue)) {
                    currentValue = currentValue.trim();
                    currentValue = '<li>' + currentValue.slice(2) + '</li>';

                    if (!orderedSubList.test(array[index - 1])) {
                        currentValue = '<ol class="list-decimal pl-4">' + currentValue;
                    }

                    if (orderedList.test(array[index + 1]) && !orderedSubList.test(array[index + 1])) {
                        currentValue = currentValue + '</ol>';
                    }

                    if (!orderedList.test(array[index + 1]) && !orderedSubList.test(array[index + 1])) {
                        currentValue = currentValue + '</ol class="list-decimal pl-4"></li></ol>';
                    }
                }

                return currentValue;
            }).join('');

            console.log(formattedList);
            content = content.replace(list, formattedList);
        });
    }

    return content.split('\n').map(line => {
        if (!h1.test(line) && !h2.test(line) && !h3.test(line) && !unorderedList.test(line) && !unorderedSubList.test(line) && !orderedList.test(line) && !orderedSubList.test(line)) {
            return line.replace(line, '<p>' + line + '</p>');
        }
    }).join('');
}


function parse2(content) {
    // Regular Expressions
    const h1 = /^#{1}[^#].*$/gm;
    const h2 = /^#{2}[^#].*$/gm;
    const h3 = /^#{3}[^#].*$/gm;
    const bold = /\*\*[^\*\n]+\*\*/gm;
    const italics = /[^\*]\*[^\*\n]+\*/gm;
    const link = /\[[\w|\(|\)|\s|\*|\?|\-|\.|\,]*(\]\(){1}[^\)]*\)/gm;
    const lists = /^((\s*((\*|\-)|\d(\.|\))) [^\n]+))+$/gm;
    const unorderedList = /^[\*|\+|\-]\s.*$/;
    const unorderedSubList = /^\s\s\s*[\*|\+|\-]\s.*$/;
    const orderedList = /^\d\.\s.*$/;
    const orderedSubList = /^\s\s+\d\.\s.*$/;

    // ... (your existing parsing logic)

    // Apply consistent Tailwind CSS classes to generated HTML elements
    content = content.replace(h1, '<h1 class="text-4xl font-bold">$1</h1>');
    content = content.replace(h2, '<h2 class="text-3xl font-semibold">$1</h2>');
    content = content.replace(h3, '<h3 class="text-2xl font-medium">$1</h3>');
    content = content.replace(bold, '<strong class="font-bold">$1</strong>');
    content = content.replace(italics, '<em class="italic">$1</em>');
    content = content.replace(link, '<a class="text-blue-500 underline" href="$1">$2</a>');
    // ... (update the rest of the parsing logic)

    // Apply Tailwind CSS classes to lists and list items
    content = content.replace(unorderedList, '<ul class="list-disc pl-4">$&');
    content = content.replace(unorderedSubList, '<ul class="list-disc pl-8">$&');
    content = content.replace(orderedList, '<ol class="list-decimal pl-4">$&');
    content = content.replace(orderedSubList, '<ol class="list-decimal pl-8">$&');
    content = content.replace('</li>', '</li><br>'); // Ensure list item closing tag

    // Apply Tailwind CSS class to paragraphs
    content = content.replace(/<p>(.*?)<\/p>/g, '<p class="text-base">$1</p>');

    return '<div class="container mx-auto py-8">' + content + '</div>';
}
function escapeHTML(unsafeText) {
    let div = document.createElement('div');
    div.textContent = unsafeText;
    return div.innerHTML;
}