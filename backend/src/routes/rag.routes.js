const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');

// Simple in-memory search index
let contentIndex = [];
let isIndexed = false;

// Index all markdown files
async function indexContent() {
  if (isIndexed) return;

  const docsPath = path.join(__dirname, '../../../my-book/docs');
  contentIndex = [];

  try {
    await indexDirectory(docsPath);
    isIndexed = true;
    console.log(`📚 Indexed ${contentIndex.length} content sections`);
  } catch (error) {
    console.error('Error indexing content:', error);
  }
}

async function indexDirectory(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      await indexDirectory(fullPath);
    } else if (entry.name.endsWith('.md') || entry.name.endsWith('.mdx')) {
      try {
        const content = await fs.readFile(fullPath, 'utf-8');

        // Extract module from path (e.g., "module-1-ros2", "intro")
        // Use path.sep or match both / and \ for cross-platform compatibility
        const normalizedPath = fullPath.replace(/\\/g, '/');
        const moduleMatch = normalizedPath.match(/\/(module-\d+-[^/]+|intro)\/?/);
        const isIntro = entry.name === 'intro.md' || normalizedPath.includes('/intro.md');
        const module = moduleMatch ? moduleMatch[1] : (isIntro ? 'intro' : null);

        // Extract title from frontmatter or first heading
        const titleMatch = content.match(/^#\s+(.+)$/m);
        const title = titleMatch ? titleMatch[1] : entry.name;

        // Split into main sections (##)
        const mainSections = content.split(/^##\s+/m);

        mainSections.forEach((section, idx) => {
          if (idx === 0 && !section.trim().startsWith('#')) return; // Skip frontmatter

          const sectionTitle = section.split('\n')[0].trim();
          const sectionContent = section.substring(sectionTitle.length).trim();

          // Index main section
          if (sectionContent.length > 50) {
            contentIndex.push({
              file: entry.name,
              title: title,
              section: sectionTitle || title,
              content: sectionContent,
              path: fullPath,
              module: module // Add module identifier
            });
          }

          // Also index subsections (###) for better granularity
          const subsections = sectionContent.split(/^###\s+/m);
          if (subsections.length > 1) {
            subsections.forEach((subsection, subIdx) => {
              if (subIdx === 0) return; // Skip content before first subsection

              const subTitle = subsection.split('\n')[0].trim();
              const subContent = subsection.substring(subTitle.length).trim();

              if (subContent.length > 50) {
                contentIndex.push({
                  file: entry.name,
                  title: title,
                  section: `${sectionTitle} > ${subTitle}`,
                  content: subContent,
                  path: fullPath,
                  module: module // Add module identifier
                });
              }
            });
          }
        });
      } catch (error) {
        console.error(`Error reading ${fullPath}:`, error);
      }
    }
  }
}

// Simple keyword search with improved scoring and module prioritization
function searchContent(query, limit = 5, currentModule = null) {
  const queryLower = query.toLowerCase();
  const keywords = queryLower.split(/\s+/).filter(k => k.length > 2);

  const results = contentIndex
    .map(item => {
      const titleLower = item.title.toLowerCase();
      const sectionLower = item.section.toLowerCase();
      const contentLower = item.content.toLowerCase();
      const fileLower = item.file.toLowerCase();

      let score = 0;

      // MODULE PRIORITIZATION: Boost content from current module significantly
      if (currentModule && item.module === currentModule) {
        score += 2000; // Large boost for current module content
      }

      // Exact title match gets highest score
      if (titleLower.includes(queryLower)) {
        score += 1000;
      }

      // Exact section match
      if (sectionLower.includes(queryLower)) {
        score += 500;
      }

      // Title keyword matches
      keywords.forEach(keyword => {
        if (titleLower.includes(keyword)) score += 50;
        if (sectionLower.includes(keyword)) score += 30;

        // Content keyword matches - escape special regex characters
        const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        try {
          const count = (contentLower.match(new RegExp(escapedKeyword, 'g')) || []).length;
          score += count * 5;
        } catch (e) {
          // If regex still fails, use simple string counting
          const parts = contentLower.split(keyword);
          score += (parts.length - 1) * 5;
        }
      });

      // Boost comprehensive book summary for broad queries
      if (fileLower.includes('book-summary')) {
        if (queryLower.includes('book') || queryLower.includes('summary') ||
            queryLower.includes('overview') || queryLower.includes('learn') ||
            queryLower.includes('modules') || queryLower.includes('course')) {
          score += 400; // High priority for book-level queries
        }
      }

      // Boost VLA/fine-tuning related content when relevant keywords present
      if (queryLower.includes('fine-tuning') || queryLower.includes('deployment') ||
          queryLower.includes('vla') || queryLower.includes('vision-language')) {
        if (fileLower.includes('vla') || fileLower.includes('finetuning') ||
            titleLower.includes('vision') || titleLower.includes('fine-tun')) {
          score += 200;
        }
      }

      // Boost specific chapters when chapter number mentioned
      const chapterMatch = queryLower.match(/chapter\s*(\d+)/);
      if (chapterMatch) {
        const chapterNum = chapterMatch[1];
        if (fileLower.includes(`chapter-0${chapterNum}`) || fileLower.includes(`chapter-${chapterNum}`)) {
          score += 300;
        }
        // But prioritize book summary if asking for chapter summary
        if (queryLower.includes('summary') && fileLower.includes('book-summary')) {
          score += 100; // Additional boost for comprehensive context
        }
      }

      return { ...item, score };
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return results;
}

// Generate answer from search results
function generateAnswer(query, searchResults, mode, selectedText) {
  if (searchResults.length === 0) {
    return 'I could not find relevant information in the book to answer your question. Please try rephrasing or ask about topics covered in the robotics course.';
  }

  // Build answer from top results
  let answer = '';

  if (mode === 'selected_text_only' && selectedText) {
    answer = `Based on the selected text:\n\n`;
  }

  const topResult = searchResults[0];
  const queryLower = query.toLowerCase();

  // Add source grounding at the start
  const sourceFile = topResult.file.replace('.md', '').replace('.mdx', '');
  const isFromBookSummary = sourceFile.includes('book-summary');
  const sourcePrefix = isFromBookSummary
    ? `**Source:** ${topResult.title}\n\n`
    : `**Source:** ${topResult.section} (${topResult.title})\n\n`;

  answer += sourcePrefix;

  // Check if this is a broad/book-level query (multiple relevant results from different chapters)
  const uniqueChapters = new Set(searchResults.map(r => r.file));
  const isBookLevelQuery = uniqueChapters.size >= 3 ||
                           queryLower.includes('book summary') ||
                           queryLower.includes('overall') ||
                           (queryLower.includes('what is') && !queryLower.includes('chapter'));

  if (isBookLevelQuery && !queryLower.match(/chapter\s*\d/)) {
    // Provide concise book-level synthesis
    const mainTopic = topResult.title.split(':')[0].trim();

    // Extract ONE best paragraph for context
    let contextPara = '';
    for (const result of searchResults.slice(0, 3)) {
      const paragraphs = result.content.split('\n\n').filter(p => {
        const trimmed = p.trim();
        return trimmed.length > 80 &&
               trimmed.length < 400 &&
               !trimmed.startsWith('```') &&
               !trimmed.match(/^(class|def|import|from|<|{|\[)/) &&
               (trimmed.includes('is ') || trimmed.includes('provides') ||
                trimmed.includes('enables') || trimmed.includes('allows'));
      });
      if (paragraphs.length > 0) {
        contextPara = paragraphs[0];
        break;
      }
    }

    if (contextPara) {
      answer += contextPara;
    } else {
      answer += `This book covers ${mainTopic.toLowerCase()}, including: ${searchResults.slice(0, 3).map(r => r.section).join(', ')}.`;
    }

    // Add concise key topics (max 4)
    answer += `\n\n**Key Topics:**\n`;
    searchResults.slice(0, 4).forEach(result => {
      answer += `• ${result.section}\n`;
    });

  } else if (queryLower.includes('summary')) {
    // Chapter/module summary - prefer comprehensive book summary context
    const hasBookSummary = searchResults.some(r => r.file.includes('book-summary'));

    if (hasBookSummary) {
      // Use book summary content for comprehensive context
      const bookSummaryResults = searchResults.filter(r => r.file.includes('book-summary'));
      const mainResult = bookSummaryResults[0] || topResult;

      // Extract 2-3 key paragraphs (concise for chatbot)
      const paragraphs = mainResult.content.split('\n\n').filter(p => {
        const trimmed = p.trim();
        return trimmed.length > 40 &&
               trimmed.length < 500 &&
               !trimmed.startsWith('```') &&
               !trimmed.startsWith('##') &&
               !trimmed.startsWith('---') &&
               !trimmed.match(/^(import|from|class |def |<[a-z]|{|\[)/);
      });

      // Add 2-3 paragraphs maximum (chatbot-friendly length)
      const contentToAdd = paragraphs.slice(0, 3);
      if (contentToAdd.length > 0) {
        answer += contentToAdd.join('\n\n');
      } else {
        answer += mainResult.content.substring(0, 400) + '...';
      }

    } else {
      // Use chapter-specific content - concise format
      const summaryMatch = topResult.content.match(/In this chapter, you learned:[\s\S]*?(?=\n\n\*\*|With these skills|$)/i);

      if (summaryMatch) {
        // Found formal summary - use it (already concise)
        answer += summaryMatch[0].trim();

        // Add brief context if available
        const contextMatch = topResult.content.match(/With these skills[^\n]+/);
        if (contextMatch) {
          answer += '\n\n' + contextMatch[0];
        }
      } else {
        // Extract key bullet points (max 5 for conciseness)
        const bulletMatch = topResult.content.match(/^[-•*]\s+.+$/gm);
        if (bulletMatch && bulletMatch.length > 2) {
          answer += bulletMatch.slice(0, 5).join('\n');
        } else {
          // Fallback: first explanatory paragraph
          const paragraphs = topResult.content.split('\n\n').filter(p =>
            p.trim().length > 50 &&
            p.trim().length < 400 &&
            !p.startsWith('```')
          );
          answer += paragraphs[0] || 'Summary content available in the chapter.';
        }
      }
    }

    // Add 2-3 related topics (concise)
    if (searchResults.length > 1) {
      answer += `\n\n**See also:** `;
      const related = searchResults.slice(1, 3).map(r => r.section).join(', ');
      answer += related;
    }

  } else {
    // Specific topic/question answer - concise and focused
    const parts = topResult.content.split('\n\n');
    let textAdded = 0;
    let codeAdded = false;

    // Add 2-3 explanatory paragraphs (chatbot-friendly)
    for (const part of parts) {
      if (textAdded >= 3) break;

      const trimmed = part.trim();
      if (trimmed.length < 30 || trimmed.startsWith('###')) continue;

      const isCode = trimmed.startsWith('```');
      const isPureCode = isCode || trimmed.match(/^(import|from|class |def |<|\{)/);

      if (isPureCode) {
        // Include ONE compact code example if relevant
        if (!codeAdded && textAdded > 0 && trimmed.length < 600) {
          answer += '\n\n' + trimmed;
          codeAdded = true;
          break; // Stop after code example
        }
      } else if (trimmed.length > 40 && trimmed.length < 500) {
        // Add concise explanatory text
        if (textAdded > 0) answer += '\n\n';
        answer += trimmed;
        textAdded++;
      }
    }

    // Fallback if no content found
    if (textAdded === 0 && searchResults.length > 1) {
      const fallback = searchResults[1].content.split('\n\n')
        .find(p => p.trim().length > 50 && p.trim().length < 400);
      if (fallback) answer += fallback;
    }

    // Add 2 related topics (concise)
    if (searchResults.length > 1) {
      answer += `\n\n**See also:** `;
      answer += searchResults.slice(1, 3).map(r => r.section).join(', ');
    }
  }

  return answer;
}

// RAG query endpoint
router.post('/query', async (req, res) => {
  try {
    const { query, mode, selected_text, module } = req.body;

    if (!query || query.trim() === '') {
      return res.status(400).json({
        success: false,
        answer: 'Please provide a valid question.'
      });
    }

    // Ensure content is indexed
    await indexContent();

    // Search for relevant content with module prioritization
    const searchResults = searchContent(query, 5, module);

    // Generate answer
    const answer = generateAnswer(query, searchResults, mode, selected_text);

    // Get sources
    const sources = searchResults.map(r => r.section).slice(0, 3);

    res.json({
      success: true,
      answer: answer,
      sources: sources,
      module: module // Echo back the module for debugging
    });

  } catch (error) {
    console.error('RAG query error:', error);
    res.status(500).json({
      success: false,
      answer: 'Sorry, there was an error processing your request. Please try again.'
    });
  }
});

module.exports = router;
