/**
 * Split text into chunks by sentence boundaries, respecting max word count per chunk.
 * @param {string} text - The text to split
 * @param {number} maxWords - Maximum words per chunk (default: 30)
 * @returns {string[]} Array of text chunks
 */
export function splitIntoChunks(text, maxWords = 30) {
  if (!text || typeof text !== 'string') return [];

  // Split by sentence boundaries: period, question mark, exclamation
  const sentenceRegex = /([.!?]+\s+|$)/;
  const sentences = text.split(sentenceRegex).filter((s) => s.trim().length > 0);

  const chunks = [];
  let currentChunk = '';

  for (const sentence of sentences) {
    // Skip standalone punctuation/whitespace
    if (!sentence.match(/\w/)) continue;

    const wordCount = currentChunk.split(/\s+/).filter((w) => w.length > 0).length;
    const sentenceWordCount = sentence.split(/\s+/).filter((w) => w.length > 0).length;

    // If adding this sentence would exceed maxWords, save current chunk and start new one
    if (wordCount + sentenceWordCount > maxWords && currentChunk.trim().length > 0) {
      chunks.push(currentChunk.trim());
      currentChunk = sentence;
    } else {
      currentChunk += sentence;
    }
  }

  // Push remaining chunk
  if (currentChunk.trim().length > 0) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}
