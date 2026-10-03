import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const repoUrl = 'https://github.com/nornir-automation/nornir';

// Read the Docs serves each version under its own path (e.g. /en/latest/) and exposes the
// full URL at build time. Everywhere else the site is served from the root.
const canonical = process.env.READTHEDOCS_CANONICAL_URL
  ? new URL(process.env.READTHEDOCS_CANONICAL_URL)
  : new URL('https://nornir.readthedocs.io/');

const config: Config = {
  title: 'Nornir',
  tagline: 'Pluggable multi-threaded framework with inventory management to help operate collections of devices',
  favicon: 'img/logo/nornir_logo_00.jpg',

  url: canonical.origin,
  baseUrl: canonical.pathname,

  organizationName: 'nornir-automation',
  projectName: 'nornir',

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  onDuplicateRoutes: 'throw',
  trailingSlash: false,

  markdown: {
    // .md files (including the pages rendered from notebooks) are parsed as CommonMark, so
    // notebook prose such as `<key, value>` or `{` never trips the MDX parser. .mdx files
    // get full MDX.
    format: 'detect',
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  headTags: [
    // Privacy-friendly analytics by Plausible, carried over from the Sphinx theme
    {
      tagName: 'script',
      attributes: {async: 'true', src: 'https://plausible.io/js/pa-nQSjr1kThG7AEcSd5eF6n.js'},
    },
    {
      tagName: 'script',
      attributes: {},
      innerHTML:
        'window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()',
    },
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          sidebarCollapsed: true,
          editUrl: `${repoUrl}/tree/main/docs/`,
          exclude: ['**/.ipynb_checkpoints/**'],
          // Files such as upgrading/2_to_3.md are not ordering prefixes
          numberPrefixParser: false,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Nornir',
      logo: {
        alt: 'Nornir logo',
        src: 'img/logo/nornir_logo_00.jpg',
      },
      items: [
        {type: 'doc', docId: 'tutorial/index', position: 'left', label: 'Tutorial'},
        {to: '/category/how-to-guides', position: 'left', label: 'How-to guides'},
        {to: '/category/api-reference', position: 'left', label: 'API reference'},
        {
          href: repoUrl,
          position: 'right',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Tutorial', to: '/tutorial'},
            {label: 'Configuration', to: '/configuration'},
            {label: 'Community plugins', to: '/community/plugin_list'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub', href: repoUrl},
            {label: 'Changelog', href: `${repoUrl}/blob/main/CHANGELOG.rst`},
            {label: 'Contributing', href: `${repoUrl}/blob/main/CONTRIBUTING.rst`},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} David Barroso and the Nornir contributors.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'toml', 'markup-templating', 'django'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
