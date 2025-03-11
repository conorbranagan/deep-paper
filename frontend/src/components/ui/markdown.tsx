import React from "react";
import ReactMarkdown from "react-markdown";
import type { CSSProperties } from "react";
import type { Components } from "react-markdown";

interface MarkdownRendererProps {
  /** The markdown content as children (string) */
  children: string;
  /** Optional additional component overrides for ReactMarkdown */
  additionalComponents?: Partial<Components>;
  /** Optional styles for the container div */
  containerStyle?: CSSProperties;
}

/*
Custom markdown wrapper so we can have nice default styles, as tailwind undoes them all.
*/
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  children,
  additionalComponents = {},
  containerStyle = {},
}) => {
  // Default styling for lists
  const defaultComponents = {
    ul: ({ ...props }) => (
      <ul
        style={{
          display: "block",
          listStyleType: "disc",
          paddingInlineStart: "40px",
        }}
        {...props}
      />
    ),
    ol: ({ ...props }) => (
      <ol
        style={{
          display: "block",
          listStyleType: "decimal",
          paddingInlineStart: "40px",
        }}
        {...props}
      />
    ),
    p: ({ ...props }) => (
      <p
        style={{
          display: "block",
          marginTop: "1em",
          marginBottom: "1em",
        }}
        {...props}
      />
    ),
    h1: ({ ...props }) => (
      <h1
        style={{
          display: "block",
          fontSize: "2em",
          marginTop: "0.67em",
          marginBottom: "0.67em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
    h2: ({ ...props }) => (
      <h2
        style={{
          display: "block",
          fontSize: "1.5em",
          marginTop: "0.83em",
          marginBottom: "0.83em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
    h3: ({ ...props }) => (
      <h3
        style={{
          display: "block",
          fontSize: "1.17em",
          marginTop: "1em",
          marginBottom: "1em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
    h4: ({ ...props }) => (
      <h4
        style={{
          display: "block",
          marginTop: "1.33em",
          marginBottom: "1.33em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
    h5: ({ ...props }) => (
      <h5
        style={{
          display: "block",
          fontSize: "0.83em",
          marginTop: "1.67em",
          marginBottom: "1.67em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
    h6: ({ ...props }) => (
      <h6
        style={{
          display: "block",
          fontSize: "0.67em",
          marginTop: "2.33em",
          marginBottom: "2.33em",
          fontWeight: "bold",
        }}
        {...props}
      />
    ),
  };

  // Merge default components with any additional components provided
  const mergedComponents = {
    ...defaultComponents,
    ...additionalComponents,
  };

  return (
    <div style={containerStyle}>
      <ReactMarkdown components={mergedComponents}>{children}</ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
