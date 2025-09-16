const CONFIG_MAP = {
  dev: {
    domain: 'localhost',
    apiBaseUrl: 'http://localhost:8012',
  },
  prod: {
    domain: '182.254.192.55',
    apiBaseUrl: 'http://182.254.192.55:8012',
  },
} as const;

type ConfigKey = keyof typeof CONFIG_MAP;

type Config = (typeof CONFIG_MAP)[ConfigKey];

function resolveEnv(): ConfigKey {
  const raw = (process.env.REACT_APP_HOLDER_ENV || process.env.HOLDER_ENV || 'dev').toLowerCase();
  return raw === 'prod' ? 'prod' : 'dev';
}

const activeEnv = resolveEnv();

export const appConfig: Config & { env: ConfigKey } = {
  ...CONFIG_MAP[activeEnv],
  env: activeEnv,
};
