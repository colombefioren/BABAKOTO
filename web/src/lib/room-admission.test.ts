import { Room, type CreateOptions } from 'livekit-server-sdk';
import { describe, expect, it, vi } from 'vitest';
import { RoomAdmission, RoomCapacityError, RoomServiceError, roomLimit } from './room-admission';
import { JOIN_TOKEN_SECONDS, type LiveKitConfig } from './token';

const config: LiveKitConfig = {
  url: 'ws://example.test',
  apiKey: 'fixture',
  apiSecret: 'x'.repeat(32),
};

function directory() {
  const rooms = new Map<string, Room>();
  return {
    rooms,
    listRooms: vi.fn(async () => [...rooms.values()]),
    createRoom: vi.fn(async (options: CreateOptions) => {
      const room = new Room({ name: options.name });
      rooms.set(room.name, room);
      return room;
    }),
  };
}

describe('room admission', () => {
  it('serializes admission across overlapping requests', async () => {
    const client = directory();
    const gate = new RoomAdmission();
    const first = gate.admit(client, config, 1);
    await expect(gate.admit(client, config, 1)).rejects.toThrow(RoomCapacityError);

    const session = await first;
    expect(client.createRoom).toHaveBeenCalledExactlyOnceWith({
      name: session.room,
      maxParticipants: 1,
      emptyTimeout: JOIN_TOKEN_SECONDS,
      departureTimeout: JOIN_TOKEN_SECONDS,
    });
    expect(session.token).toBeTruthy();
  });

  it('stores only the selected configuration ID in room metadata', async () => {
    const client = directory();
    const selected = '00000000-0000-0000-0000-000000000001';
    await new RoomAdmission().admit(client, config, 1, selected);
    expect(client.createRoom).toHaveBeenCalledWith(
      expect.objectContaining({ metadata: JSON.stringify({ babakoto_agent_id: selected }) }),
    );
  });

  it('counts existing rooms after the issuer is restarted', async () => {
    const client = directory();
    client.rooms.set('other-room', new Room({ name: 'other-room' }));
    const gate = new RoomAdmission();
    await expect(gate.admit(client, config, 1)).rejects.toThrow(RoomCapacityError);
    expect(client.createRoom).not.toHaveBeenCalled();

    client.rooms.delete('other-room');
    await expect(gate.admit(client, config, 1)).resolves.toMatchObject({ url: config.url });
  });

  it('returns no token when the room service fails and allows a later retry', async () => {
    const client = directory();
    const gate = new RoomAdmission();
    client.listRooms.mockRejectedValueOnce(new Error('internal details'));
    await expect(gate.admit(client, config, 1)).rejects.toThrow(RoomServiceError);
    expect(client.createRoom).not.toHaveBeenCalled();
    client.createRoom.mockRejectedValueOnce(new Error('internal details'));
    await expect(gate.admit(client, config, 1)).rejects.toThrow(RoomServiceError);
    await expect(gate.admit(client, config, 1)).resolves.toMatchObject({ url: config.url });
  });

  it('accepts only a positive configured ceiling within the supported range', () => {
    expect(roomLimit({})).toBe(4);
    expect(roomLimit({ WEB_MAX_PLAYGROUND_ROOMS: '12' })).toBe(12);
    for (const invalid of ['0', '101', '2.0', '2x', '']) {
      expect(() => roomLimit({ WEB_MAX_PLAYGROUND_ROOMS: invalid })).toThrow();
    }
  });
});
