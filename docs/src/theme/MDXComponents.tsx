import React, {type ReactNode} from 'react';
import MDXComponents from '@theme-original/MDXComponents';

// mdxify emits Mintlify's <Icon icon="github" /> next to every API heading as a link to the
// source. Render it as an inline GitHub mark; it contributes no text, so heading anchors stay
// the plain symbol name (#task, #run, ...).
function Icon({icon}: {icon: string}): ReactNode {
  if (icon !== 'github') {
    return null;
  }
  return <span className="source-link-icon" role="img" aria-label="View source on GitHub" />;
}

export default {
  ...MDXComponents,
  Icon,
};
