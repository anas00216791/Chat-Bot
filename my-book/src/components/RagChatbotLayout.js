import React from 'react';
import Layout from '@theme/Layout';
import RagChatbot from './RagChatbot';

export default function RagChatbotLayout(props) {
  return (
    <Layout {...props}>
      {props.children}
      <RagChatbot />
    </Layout>
  );
}