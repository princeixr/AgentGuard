import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export function Chart({
  option,
  style,
}: {
  option: Record<string, unknown>;
  style?: React.CSSProperties;
}) {
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={style}
      notMerge
      lazyUpdate
    />
  );
}
