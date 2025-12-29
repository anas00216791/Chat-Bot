// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'AI-Powered Robotics',
  tagline: 'Building Intelligent Machines',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'https://your-docusaurus-site.vercel.app',
  // Set the /<baseUrl>/ pathname under which your site is served
  baseUrl: '/',

  // GitHub pages deployment config.
  organizationName: 'your-org', // Usually your GitHub org/user name.
  projectName: 'my-book', // Usually your repo name.

  onBrokenLinks: 'throw',

  // Custom fields for client-side access
  customFields: {
    apiUrl: process.env.API_URL || 'http://localhost:5000/api',
  },

  // Markdown configuration
  markdown: {
    format: 'mdx',
  },

  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      '@docusaurus/preset-classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],


  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'AI-Powered Robotics',
        items: [
          {
            to: '/',
            label: 'Home',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Modules',
          },
          {
            to: '/about',
            label: 'About',
            position: 'left',
          },
          {
            to: '/contact',
            label: 'Contact',
            position: 'left',
          },
          {
            to: '/login',
            label: 'Login',
            position: 'right',
          },
          {
            to: '/signup',
            label: 'Sign Up',
            position: 'right',
            className: 'button button--primary',
          },
        ],
      },
      footer: {
        style: 'dark',
        copyright: `© 2025 AI-Powered Robotics Course. All rights reserved.`,
      },
    }),
};

module.exports = config;
