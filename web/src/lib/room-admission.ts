import { RoomServiceClient } from 'livekit-server-sdk';
import {
  ConfigError,
  createSession,
  JOIN_TOKEN_SECONDS,
  type LiveKitConfig,
  type Session,
} from './token';

type RoomService = Pick<RoomServiceClient, 'listRooms' | 'createRoom'>;

export class RoomCapacityError extends Error {}
export class RoomServiceError extends Error {}

export function roomLimit(env: Record<string, string | undefined> = process.env): number {
  const raw = env.WEB_MAX_PLAYGROUND_ROOMS ?? '4';
  const limit = Number(raw);
  if (!/^[1-9][0-9]*$/.test(raw) || !Number.isSafeInteger(limit) || limit > 100) {
    throw new ConfigError('WEB_MAX_PLAYGROUND_ROOMS must be an integer from 1 to 100');
  }
  return limit;
}

export function roomService(config: LiveKitConfig): RoomService {
  return new RoomServiceClient(
    process.env.LIVEKIT_ROOM_SERVICE_URL || config.url,
    config.apiKey,
    config.apiSecret,
    { requestTimeout: 5, failover: false },
  );
}

/** One issuer checks and creates rooms serially. LiveKit retains the admitted rooms across restarts. */
export class RoomAdmission {
  private busy = false;

  async admit(
    client: RoomService,
    config: LiveKitConfig,
    maximum: number,
    selectedAgentId?: string,
  ): Promise<Session> {
    if (this.busy) throw new RoomCapacityError('Room admission is busy. Try again shortly.');
    this.busy = true;
    try {
      const rooms = await client.listRooms();
      if (rooms.length >= maximum) {
        throw new RoomCapacityError('All playground rooms are in use. Try again shortly.');
      }
      const session = await createSession(config);
      const room = await client.createRoom({
        name: session.room,
        emptyTimeout: JOIN_TOKEN_SECONDS,
        departureTimeout: JOIN_TOKEN_SECONDS,
        maxParticipants: 1,
        ...(selectedAgentId
          ? { metadata: JSON.stringify({ babakoto_agent_id: selectedAgentId }) }
          : {}),
      });
      if (room.name !== session.room) throw new Error('LiveKit returned an unexpected room');
      return session;
    } catch (error) {
      if (error instanceof RoomCapacityError) throw error;
      throw new RoomServiceError('LiveKit could not allocate a room. Try again shortly.');
    } finally {
      this.busy = false;
    }
  }
}
