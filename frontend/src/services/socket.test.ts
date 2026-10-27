import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createReconnectingSocket, type SocketStatus } from "./socket";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.onclose?.({ code: 1006 });
  }
}

describe("createReconnectingSocket", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("transmet les messages et se reconnecte avec un délai croissant", () => {
    const statuses: SocketStatus[] = [];
    const messages: unknown[] = [];
    const onReconnect = vi.fn();
    const stop = createReconnectingSocket({
      url: "ws://test/ws/news/EURUSD",
      onMessage: (data) => messages.push(data),
      onStatus: (status) => statuses.push(status),
      onReconnect,
    });

    const first = FakeWebSocket.instances[0];
    first.onopen?.();
    first.onmessage?.({ data: JSON.stringify({ type: "ping" }) });
    expect(messages).toEqual([{ type: "ping" }]);

    first.close();
    expect(statuses[statuses.length - 1]).toBe("offline");
    vi.advanceTimersByTime(999);
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(2);

    FakeWebSocket.instances[1].onopen?.();
    expect(onReconnect).toHaveBeenCalledTimes(1);

    stop();
    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("ne se reconnecte pas pour un marché inconnu (4404)", () => {
    createReconnectingSocket({ url: "ws://test", onMessage: () => {}, onStatus: () => {} });
    FakeWebSocket.instances[0].onclose?.({ code: 4404 });
    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
