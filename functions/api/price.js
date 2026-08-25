export async function onRequest(context) {
  const { env } = context;
  const res = await fetch(`https://finnhub.io/api/v1/quote?symbol=BNO&token=${env.FINNHUB_KEY}`);
  const data = await res.json();
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" }
  });
}
