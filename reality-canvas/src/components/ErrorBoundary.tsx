import { Component, type ErrorInfo, type ReactNode } from "react";
import { ERROR_BOUNDARY_RETRY, ERROR_BOUNDARY_TITLE } from "../constants";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.debug("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" style={{ padding: 24, color: "#e9eef7" }}>
          <p>{ERROR_BOUNDARY_TITLE}</p>
          <button onClick={() => location.reload()}>{ERROR_BOUNDARY_RETRY}</button>
        </div>
      );
    }
    return this.props.children;
  }
}
