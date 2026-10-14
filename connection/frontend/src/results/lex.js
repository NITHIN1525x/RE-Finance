import { marked } from 'marked'

// marked is used ONLY as a lexer: Markdown text -> tokens. Markdown.jsx turns the tokens into React elements,
// so no HTML string is ever produced.
export const lex = (text) => marked.lexer(text || '', { gfm: true })
