import React from 'react';
import ReactDOM from 'react-dom/client';
import ModulesChatbot from '../components/ModulesChatbot';
import ExecutionEnvironment from '@docusaurus/ExecutionEnvironment';

let chatbotRoot = null;

export function onRouteDidUpdate({ location }) {
  if (!ExecutionEnvironment.canUseDOM) {
    return;
  }

  // Determine if we're on a documentation page
  const isDocPage = location.pathname.startsWith('/intro') ||
                    location.pathname.startsWith('/module-') ||
                    location.pathname.startsWith('/chatbot-integration');

  // Pages to EXCLUDE from chatbot
  const excludedPages = [
    '/login',
    '/signup',
    '/about',
    '/contact',
    '/privacy',
    '/terms'
  ];

  const isExcludedPage = excludedPages.some(page => location.pathname.startsWith(page));
  const isHomePage = location.pathname === '/';

  // Show chatbot only on doc pages, not on excluded pages or home
  const showChatbot = isDocPage && !isExcludedPage && !isHomePage;

  // Get or create chatbot container
  let chatbotContainer = document.getElementById('chatbot-root');

  if (showChatbot) {
    if (!chatbotContainer) {
      chatbotContainer = document.createElement('div');
      chatbotContainer.id = 'chatbot-root';
      document.body.appendChild(chatbotContainer);

      // Create root only once
      if (!chatbotRoot) {
        chatbotRoot = ReactDOM.createRoot(chatbotContainer);
      }
    }

    // Render or update chatbot
    if (chatbotRoot) {
      chatbotRoot.render(<ModulesChatbot />);
    }
  } else {
    // Unmount chatbot if it exists
    if (chatbotRoot && chatbotContainer) {
      chatbotRoot.unmount();
      chatbotRoot = null;
      chatbotContainer.remove();
    }
  }
}
