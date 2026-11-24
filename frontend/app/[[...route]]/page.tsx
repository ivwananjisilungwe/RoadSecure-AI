import { notFound } from "next/navigation";
import { RoadSecure } from "../../components/console";

const pages = new Set(["dashboard", "login", "events", "alerts", "simulator", "incidents", "reports", "evaluation", "settings"]);
const detailPages = new Set(["events", "alerts", "incidents"]);

export default async function Page({ params }: { params: Promise<{ route?: string[] }> }) {
  const { route = [] } = await params;
  const [page = "dashboard", id, extra] = route;
  if (!pages.has(page) || extra || (id && (!detailPages.has(page) || !/^\d+$/.test(id)))) notFound();
  return <RoadSecure page={page} id={id} />;
}
