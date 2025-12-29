import React from 'react';
import {useLocation} from '@docusaurus/router';
import ModulesChatbot from '../components/ModulesChatbot';

// Root component wraps the entire application
// Chatbot appears only on documentation/modules pages (intro and all modules)
export default function Root({children}) {
  const location = useLocation();

  // Determine if we're on a documentation page
  // Documentation includes: /intro, /module-1-ros2, /module-2-gazebo-unity, etc.
  const isDocPage = location.pathname.startsWith('/intro') ||
                    location.pathname.startsWith('/module-') ||
                    location.pathname.startsWith('/chatbot-integration');

  // Pages to EXCLUDE from chatbot (even if they might match doc patterns)
  const excludedPages = [
    '/login',
    '/signup',
    '/about',
    '/contact',
    '/privacy',
    '/terms'
  ];

  const isExcludedPage = excludedPages.some(page => location.pathname.startsWith(page));

  // Also exclude the home page (exact match for '/')
  const isHomePage = location.pathname === '/';

  // Show chatbot only on doc pages, not on excluded pages or home
  const showChatbot = isDocPage && !isExcludedPage && !isHomePage;

  return (
    <>
      {children}
      {showChatbot && <ModulesChatbot />}
    </>
  );
}
