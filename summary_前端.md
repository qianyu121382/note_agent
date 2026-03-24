# Frontend Visualization for LangGraph Pipelines - Summary

This document summarizes the approach for building a frontend UI to visualize the execution of a LangGraph agent pipeline. The goal is to provide real-time feedback to the user by showing the status and output of each step in the graph.

## Core Concepts

The UI is built around two main visual components:

1.  **Pipeline Progress Bar**: A top-level bar that shows the status of the entire pipeline at a glance. Each segment represents a node and is color-coded based on its status (e.g., idle, running, complete).
2.  **Node Cards**: Individual cards for each step (node) in the pipeline. Each card displays the node's name, its current status, and the content it generates.

## Technical Implementation

### Data Flow with `useStream`

- The frontend connects to the LangGraph backend using a `useStream` hook.
- This hook is the primary source of data and provides three key things:
    1.  `messages`: An array of message objects, including the streaming content (tokens) from the agent.
    2.  `values`: A record containing the final, completed output from each node once it has finished executing.
    3.  `getMessagesMetadata`: A function to get metadata associated with each message. This is crucial for identifying which node produced a specific token.

### Mapping Graph Nodes to UI

- A configuration array (e.g., `PIPELINE_NODES`) is defined in the frontend. This array maps the internal node names from the LangGraph (e.g., `"do_research"`) to UI-friendly labels (e.g., `"Research"`) and the corresponding keys in the agent's state (e.g., `"research"`).

```javascript
const PIPELINE_NODES = [
  { name: "classify", stateKey: "classification", label: "Classify" },
  { name: "do_research", stateKey: "research", label: "Research" },
  { name: "analyze", stateKey: "analysis", label: "Analyze" },
  { name: "synthesize", stateKey: "synthesis", label: "Synthesize" },
];
```

### Determining Node Status

The status of each node is determined dynamically based on the data from `useStream`:

- **`complete`**: If the final output for the node's `stateKey` exists in the `values` object.
- **`streaming`**: If there is no final output yet, but new tokens for that `node.name` are currently arriving in the `messages` stream.
- **`idle`**: If neither of the above is true.

### Component Breakdown

- **`PipelineChat` (Main Component)**:
    - Initializes the `useStream` hook.
    - Renders the `PipelineProgress` bar and the `NodeCardList`.
    - Passes down the necessary data (`nodes`, `messages`, `values`, `getMetadata`).

- **`PipelineProgress` (Progress Bar)**:
    - Maps over the `PIPELINE_NODES` array.
    - For each node, it determines the status.
    - Renders a colored and labeled segment representing the node's state.

- **`NodeCardList` (Card Container)**:
    - Contains the logic to route streaming content to the correct node.
    - It creates a `streamingContent` object that maps node names to their current streaming text.
    - It maps over the `PIPELINE_NODES` and renders a `NodeCard` for each one.

- **`NodeCard` (Individual Card)**:
    - Displays the node's label and a status badge (`Waiting`, `Running`, `Done`).
    - Renders the content. It shows the `streamingContent` as it arrives for live updates and switches to the final `completedContent` from `values` once the node is done.
    - The card body can be collapsed to manage screen space.

## Summary for AI

To implement the frontend, you will need to:

1.  Create a main component that uses a data streaming hook (`useStream`).
2.  Define a configuration array that describes the nodes in your LangGraph pipeline.
3.  Implement a `PipelineProgress` component that visualizes the overall status.
4.  Implement a `NodeCard` component to display the status and output of a single node.
5.  Use the metadata from the stream to correctly route streaming output to the corresponding `NodeCard`.
6.  Determine each node's status (`idle`, `streaming`, `complete`) by checking for streaming tokens and final output values.
7.  The UI should be built with a modern frontend framework like React, Vue, Svelte, or Angular.
