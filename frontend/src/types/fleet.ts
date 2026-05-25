export type VehicleStatus = "available" | "rented" | "maintenance";

export type Car = {
  id: string;
  model: string;
  year: number;
  status: VehicleStatus;
};

export type Rental = {
  id: string;
  car_id: string;
  customer_name: string;
  start_date: string;
  end_date: string | null;
};

export type CarCreatePayload = {
  model: string;
  year: number;
  status: VehicleStatus;
};

export type CarUpdatePayload = {
  model?: string;
  year?: number;
  status?: VehicleStatus;
};

export type RentalCreatePayload = {
  car_id: string;
  customer_name: string;
  start_date: string;
};
